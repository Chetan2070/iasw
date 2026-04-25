"""
Document Processing Graph

Main LangGraph definition for the document processing pipeline.

Supports two architectures:
1. Linear Pipeline (default=off): Sequential nodes with conditional routing
2. Supervisor-Agent Architecture (default=on): Supervisor orchestrates specialized agents
"""

import logging
from datetime import datetime
from typing import Dict, Any

from langgraph.graph import StateGraph, END
from typing import Optional, Callable

from app.agents.state import ProcessingState, create_initial_state
from app.agents.nodes.validation import validation_node, route_after_validation
from app.agents.nodes.ocr import ocr_node, fallback_ocr_node, route_after_ocr
from app.agents.nodes.metadata import metadata_node
from app.agents.nodes.classifier import classifier_node, route_after_classifier
from app.agents.nodes.extractor import extractor_node
from app.agents.nodes.forgery import forgery_node
from app.agents.nodes.scorer import scorer_node
from app.agents.nodes.summary import summary_node
from app.config import settings

logger = logging.getLogger(__name__)


async def save_results_node(state: ProcessingState) -> Dict[str, Any]:
    """
    Final node - marks processing as complete.

    This node doesn't save to DB directly (that's done by the Celery task),
    but it marks the processing as complete and records the timestamp.
    """
    request_id = state.get('request_id', 'unknown')
    logger.info(f"[{request_id}] Processing complete")

    return {
        "processing_completed_at": datetime.utcnow().isoformat(),
        "current_step": "complete",
    }


def build_processing_graph() -> StateGraph:
    """
    Build the document processing LangGraph.

    Graph Structure:
        START
          │
          ▼
        validation ─── FAIL ──▶ END
          │
          │ PASS
          ▼
        parallel_start (runs OCR + metadata concurrently)
          │
          ├── ocr ─── LOW_CONF ──▶ fallback_ocr
          │                            │
          └── metadata                 │
                 │                     │
                 └─────────┬───────────┘
                           ▼
                       classifier ─── DOC_TYPE_MISMATCH ──┐
                           │                              │
                           │ OK                           │
                           ▼                              │
                       extractor                          │
                           │                              │
                           ▼                              │
                        forgery                           │
                           │                              │
                           └──────────┬───────────────────┘
                                      ▼
                                   scorer
                                      │
                                      ▼
                                   summary
                                      │
                                      ▼
                                save_results
                                      │
                                      ▼
                                     END

    Note: OCR and metadata run sequentially for simplicity (true LangGraph
    parallelism requires Send API). Metadata is fast (~10ms) so impact is minimal.

    Returns:
        Compiled StateGraph
    """
    # Create graph
    graph = StateGraph(ProcessingState)

    # Add nodes
    graph.add_node("validation", validation_node)
    graph.add_node("metadata", metadata_node)  # Runs before OCR (fast, ~10ms)
    graph.add_node("ocr", ocr_node)
    graph.add_node("fallback_ocr", fallback_ocr_node)
    graph.add_node("classifier", classifier_node)
    graph.add_node("extractor", extractor_node)
    graph.add_node("forgery", forgery_node)
    graph.add_node("scorer", scorer_node)
    graph.add_node("summary", summary_node)
    graph.add_node("save_results", save_results_node)

    # Set entry point
    graph.set_entry_point("validation")

    # Add conditional edges from validation
    graph.add_conditional_edges(
        "validation",
        route_after_validation,
        {
            "continue": "metadata",  # Run metadata first (fast)
            "fail": END,
        }
    )

    # Metadata leads to OCR
    graph.add_edge("metadata", "ocr")

    # Add conditional edges from OCR
    graph.add_conditional_edges(
        "ocr",
        route_after_ocr,
        {
            "continue": "classifier",
            "fallback": "fallback_ocr",
        }
    )

    # Fallback OCR leads to classifier
    graph.add_edge("fallback_ocr", "classifier")

    # Add conditional edges from classifier (dynamic routing)
    # Skip forgery detection if document type doesn't match
    graph.add_conditional_edges(
        "classifier",
        route_after_classifier,
        {
            "continue": "extractor",      # Normal flow
            "skip_forgery": "scorer",     # Skip forgery on type mismatch
        }
    )

    # Extractor leads to forgery (normal flow)
    graph.add_edge("extractor", "forgery")
    graph.add_edge("forgery", "scorer")
    graph.add_edge("scorer", "summary")
    graph.add_edge("summary", "save_results")
    graph.add_edge("save_results", END)

    return graph


class DocumentProcessingPipeline:
    """
    Document processing pipeline using LangGraph.

    This class wraps the LangGraph for easier use and provides
    methods for running the pipeline.
    """

    # Human-readable step names for UI display
    STEP_DISPLAY_NAMES = {
        "validation": "Validating Document",
        "metadata": "Extracting Metadata",
        "ocr": "Running OCR",
        "fallback_ocr": "Running Fallback OCR",
        "classifier": "Classifying Document",
        "extractor": "Extracting Fields",
        "forgery": "Detecting Forgery",
        "scorer": "Calculating Scores",
        "summary": "Generating Summary",
        "save_results": "Finalizing Results",
        "complete": "AI Verification Complete",
    }

    def __init__(self):
        """Initialize the pipeline."""
        self.graph = build_processing_graph()
        self.compiled_graph = self.graph.compile()
        logger.info("Document processing pipeline initialized")

    async def process(
        self,
        request_id: str,
        customer_id: str,
        change_type: str,
        document_type: str,
        requested_old_value: str,
        requested_new_value: str,
        document_path: str,
        on_step_change: Optional[Callable[[str, str], None]] = None,
    ) -> ProcessingState:
        """
        Process a document through the pipeline.

        Args:
            request_id: The request ID
            customer_id: Customer ID
            change_type: Type of change (e.g., LEGAL_NAME)
            document_type: Type of document (e.g., MARRIAGE_CERTIFICATE)
            requested_old_value: Current value to change
            requested_new_value: New value requested
            document_path: Path to the uploaded document
            on_step_change: Optional callback(request_id, step_display_name) called when step changes

        Returns:
            Final ProcessingState with all results
        """
        logger.info(f"[{request_id}] Starting document processing pipeline")

        # Create initial state
        initial_state = create_initial_state(
            request_id=request_id,
            customer_id=customer_id,
            change_type=change_type,
            document_type=document_type,
            requested_old_value=requested_old_value,
            requested_new_value=requested_new_value,
            document_path=document_path,
        )

        # Run the graph with streaming to track step changes
        try:
            final_state = None
            last_step = None

            async for event in self.compiled_graph.astream(initial_state):
                # event is a dict with node name as key and output as value
                for node_name, node_output in event.items():
                    # Get current step from output or use node name
                    current_step = node_output.get('current_step', node_name) if isinstance(node_output, dict) else node_name

                    # Update step if changed
                    if current_step != last_step:
                        display_name = self.STEP_DISPLAY_NAMES.get(current_step, current_step.replace('_', ' ').title())
                        logger.info(f"[{request_id}] Step: {display_name}")

                        if on_step_change:
                            try:
                                on_step_change(request_id, display_name)
                            except Exception as e:
                                logger.warning(f"[{request_id}] Failed to update step callback: {e}")

                        last_step = current_step

                    # Keep track of state updates
                    if isinstance(node_output, dict):
                        if final_state is None:
                            final_state = dict(initial_state)
                        final_state.update(node_output)

            # Final step update
            if on_step_change:
                try:
                    on_step_change(request_id, self.STEP_DISPLAY_NAMES.get("complete", "Complete"))
                except Exception as e:
                    logger.warning(f"[{request_id}] Failed to update final step callback: {e}")

            logger.info(f"[{request_id}] Pipeline completed successfully")
            return final_state or initial_state

        except Exception as e:
            logger.exception(f"[{request_id}] Pipeline failed")
            # Return partial state with error
            initial_state['errors'] = initial_state.get('errors', []) + [str(e)]
            initial_state['current_step'] = 'failed'
            return initial_state

    def get_graph_visualization(self) -> str:
        """
        Get a text representation of the graph structure.

        Returns:
            ASCII art representation of the graph
        """
        return """
        Document Processing Pipeline
        ============================

        START
          │
          ▼
        ┌─────────────┐
        │ validation  │ ─── FAIL ──▶ END (VALIDATION_FAILED)
        └──────┬──────┘
               │ PASS
               ▼
        ┌─────────────┐
        │    ocr      │ ─── LOW_CONF ──▶ fallback_ocr ─┐
        └──────┬──────┘                                │
               │ OK                                    │
               ▼                                       │
        ┌─────────────┐ ◀──────────────────────────────┘
        │ classifier  │ ─── DOC_TYPE_MISMATCH ─┐
        └──────┬──────┘                        │
               │ OK                            │
               ▼                               │
        ┌─────────────┐                        │
        │ extractor   │                        │
        └──────┬──────┘                        │
               │                               │
               ▼                               │
        ┌─────────────┐                        │
        │  forgery    │                        │
        └──────┬──────┘                        │
               │                               │
               ▼                               │
        ┌─────────────┐ ◀──────────────────────┘
        │   scorer    │
        └──────┬──────┘
               │
               ▼
        ┌─────────────┐
        │  summary    │
        └──────┬──────┘
               │
               ▼
        ┌─────────────┐
        │save_results │
        └──────┬──────┘
               │
               ▼
              END (AI_VERIFIED_PENDING_HUMAN)
        """


# Dynamically choose pipeline based on config
if settings.USE_SUPERVISOR_AGENTS:
    logger.info("Using Supervisor-Agent architecture")
    from app.agents.specialized.supervisor import SupervisorPipeline
    pipeline = SupervisorPipeline()
else:
    logger.info("Using Linear Pipeline architecture")
    pipeline = DocumentProcessingPipeline()
