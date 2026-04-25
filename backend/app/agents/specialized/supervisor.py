"""
Supervisor Agent

A LangGraph supervisor that orchestrates specialized worker agents
(OCR, Classifier, Extractor, Forgery, Scorer) to process documents.
"""

import logging
import operator
from typing import TypedDict, Annotated, Sequence, Dict, Any, Literal
from datetime import datetime

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END

from app.agents.state import ProcessingState, create_initial_state
from app.agents.prompts import (
    OCR_AGENT_PROMPT,
    CLASSIFIER_AGENT_PROMPT,
    EXTRACTOR_AGENT_PROMPT,
    FORGERY_AGENT_PROMPT,
    SCORER_AGENT_PROMPT,
)
from app.agents.specialized.worker_agents import (
    create_ocr_agent,
    create_classifier_agent,
    create_extractor_agent,
    create_forgery_agent,
    create_scorer_agent,
)
from app.config import settings

logger = logging.getLogger(__name__)


class SupervisorState(TypedDict, total=False):
    """State for the supervisor graph."""
    # Original request data
    request_id: str
    customer_id: str
    change_type: str
    document_type: str
    requested_old_value: str
    requested_new_value: str
    document_path: str

    # Validation
    validation_passed: bool
    validation_errors: list

    # Processing results
    ocr_text: str
    ocr_confidence: float
    ocr_method: str
    detected_document_type: str
    classification_confidence: float
    classification_match: bool
    extracted_old_value: str
    extracted_new_value: str
    extraction_confidence: float
    extracted_fields: dict
    forgery_score: float
    forgery_result: str
    forgery_details: dict
    overall_score: float
    old_name_match_score: float
    new_name_match_score: float
    risk_tier: str
    ai_recommendation: str
    ai_summary: str

    # Tracking
    flags: list
    errors: list
    current_step: str
    processing_started_at: str
    processing_completed_at: str
    llm_calls: list


def create_supervisor_graph():
    """
    Create the supervisor LangGraph that orchestrates worker agents.

    The supervisor routes tasks to specialized agents in sequence:
    1. Validation → 2. OCR → 3. Classifier → 4. Extractor → 5. Forgery → 6. Scorer → 7. Summary

    Returns:
        Compiled StateGraph
    """
    # Create worker agents
    ocr_agent = create_ocr_agent()
    classifier_agent = create_classifier_agent()
    extractor_agent = create_extractor_agent()
    forgery_agent = create_forgery_agent()
    scorer_agent = create_scorer_agent()

    def update_step_in_db(request_id: str, step: str):
        """Update the current processing step in DB for real-time updates."""
        try:
            from app.workers.tasks import update_processing_step
            update_processing_step(request_id, step)
        except Exception as e:
            logger.warning(f"[{request_id}] Could not update step in DB: {e}")

    async def validation_node(state: SupervisorState) -> Dict[str, Any]:
        """Validate the request before processing."""
        request_id = state.get('request_id', 'unknown')
        document_path = state.get('document_path', '')

        update_step_in_db(request_id, "validation")
        logger.info(f"[{request_id}] Supervisor: Running validation")
        logger.info(f"[{request_id}] Document path: {document_path}")

        import os
        errors = []
        flags = list(state.get('flags', []))

        if not document_path:
            errors.append("No document path provided")
            logger.error(f"[{request_id}] Validation failed: No document path")
        elif not os.path.exists(document_path):
            errors.append(f"Document not found: {document_path}")
            logger.error(f"[{request_id}] Validation failed: Document not found at {document_path}")

        if not state.get('customer_id'):
            errors.append("No customer ID provided")
            logger.error(f"[{request_id}] Validation failed: No customer ID")

        if errors:
            logger.error(f"[{request_id}] Validation errors: {errors}")
            return {
                "validation_passed": False,
                "validation_errors": errors,
                "errors": state.get('errors', []) + errors,
                "current_step": "validation_failed",
            }

        logger.info(f"[{request_id}] Validation passed, continuing to OCR")
        return {
            "validation_passed": True,
            "validation_errors": [],
            "current_step": "validation",
        }

    async def ocr_node(state: SupervisorState) -> Dict[str, Any]:
        """Run OCR agent to extract text."""
        request_id = state.get('request_id', 'unknown')
        document_path = state.get('document_path', '')

        update_step_in_db(request_id, "ocr")
        logger.info(f"[{request_id}] Supervisor: Delegating to OCR agent")

        try:
            task = f"""{OCR_AGENT_PROMPT}

Task: Extract text from this document.
Document path: {document_path}

Use your tools to extract the text and assess quality."""

            result = await ocr_agent.ainvoke({
                "messages": [HumanMessage(content=task)]
            })

            # Parse agent response
            final_message = result["messages"][-1]
            response_text = final_message.content if hasattr(final_message, 'content') else str(final_message)

            # Extract actual OCR results from tool calls
            ocr_text = ""
            ocr_confidence = 0.0
            ocr_method = "agent_ocr"

            for msg in result["messages"]:
                if hasattr(msg, 'tool_calls'):
                    for tool_call in msg.tool_calls:
                        if 'extract_text' in str(tool_call):
                            pass  # Results come from tool messages
                if hasattr(msg, 'content') and isinstance(msg.content, str):
                    if '"text"' in msg.content or '"success"' in msg.content:
                        import json
                        try:
                            data = json.loads(msg.content)
                            if data.get('success'):
                                ocr_text = data.get('text', '')
                                ocr_confidence = data.get('confidence', 0.0)
                        except:
                            pass

            # Fallback: use the direct OCR function if agent didn't extract properly
            if not ocr_text:
                from app.agents.specialized.ocr_tools import extract_text_from_document
                ocr_result = extract_text_from_document.invoke(document_path)
                if ocr_result.get('success'):
                    ocr_text = ocr_result.get('text', '')
                    ocr_confidence = ocr_result.get('confidence', 0.0)
                    ocr_method = ocr_result.get('method', 'fallback_ocr')

            logger.info(f"[{request_id}] OCR extracted {len(ocr_text)} chars, confidence: {ocr_confidence:.2f}")
            logger.info(f"[{request_id}] OCR text preview: {ocr_text[:500]}...")

            flags = list(state.get('flags', []))
            if ocr_confidence < 0.6:
                flags.append("OCR_LOW_QUALITY")

            return {
                "ocr_text": ocr_text,
                "ocr_confidence": float(ocr_confidence),
                "ocr_method": ocr_method,
                "flags": flags,
                "current_step": "ocr_agent",
            }

        except Exception as e:
            logger.error(f"[{request_id}] OCR agent error: {e}")
            return {
                "ocr_text": "",
                "ocr_confidence": 0.0,
                "errors": state.get('errors', []) + [f"OCR failed: {str(e)}"],
                "current_step": "ocr_agent",
            }

    async def classifier_node(state: SupervisorState) -> Dict[str, Any]:
        """Run Classifier agent to determine document type."""
        request_id = state.get('request_id', 'unknown')
        ocr_text = state.get('ocr_text', '')
        declared_type = state.get('document_type', '')

        update_step_in_db(request_id, "classifier")
        logger.info(f"[{request_id}] Supervisor: Delegating to Classifier agent")

        try:
            task = f"""{CLASSIFIER_AGENT_PROMPT}

Task: Classify this document.
Declared type: {declared_type}
OCR text (first 2000 chars): {ocr_text[:2000]}

Use your tools to analyze and classify the document."""

            result = await classifier_agent.ainvoke({
                "messages": [HumanMessage(content=task)]
            })

            # Fallback: use tools directly
            from app.agents.specialized.classifier_tools import (
                analyze_document_keywords,
                determine_document_type,
            )
            keyword_analysis = analyze_document_keywords.invoke(ocr_text[:4000])
            classification = determine_document_type.invoke({
                "keyword_analysis": keyword_analysis,
                "declared_type": declared_type,
            })

            detected_type = classification.get('detected_type', declared_type)
            confidence = classification.get('confidence', 0.5)
            is_match = classification.get('is_match', True)

            logger.info(f"[{request_id}] Classification: declared='{declared_type}', detected='{detected_type}', match={is_match}, conf={confidence:.2f}")

            flags = list(state.get('flags', []))
            if not is_match:
                flags.append("DOC_TYPE_MISMATCH")
                logger.warning(f"[{request_id}] Document type mismatch: declared '{declared_type}' vs detected '{detected_type}'")
            if confidence < 0.7:
                flags.append("DOC_TYPE_UNCERTAIN")

            return {
                "detected_document_type": detected_type,
                "classification_confidence": float(confidence),
                "classification_match": is_match,
                "flags": flags,
                "current_step": "classifier_agent",
            }

        except Exception as e:
            logger.error(f"[{request_id}] Classifier agent error: {e}")
            return {
                "detected_document_type": declared_type,
                "classification_confidence": 0.5,
                "classification_match": True,
                "errors": state.get('errors', []) + [f"Classification failed: {str(e)}"],
                "current_step": "classifier_agent",
            }

    async def extractor_node(state: SupervisorState) -> Dict[str, Any]:
        """Run Extractor agent to extract names using LLM semantic understanding."""
        request_id = state.get('request_id', 'unknown')
        ocr_text = state.get('ocr_text', '')
        requested_old = state.get('requested_old_value', '')
        requested_new = state.get('requested_new_value', '')
        doc_type = state.get('detected_document_type') or state.get('document_type', '')

        update_step_in_db(request_id, "extractor")
        logger.info(f"[{request_id}] Supervisor: Delegating to Extractor agent (LLM-based)")

        try:
            # Use LLM-based extraction for semantic understanding
            from app.agents.specialized.extractor_tools import extract_names_with_llm

            extraction_result = extract_names_with_llm.invoke({
                "text": ocr_text,
                "document_type": doc_type,
                "requested_old": requested_old,
                "requested_new": requested_new,
            })

            old_name_data = extraction_result.get('old_name', {})
            new_name_data = extraction_result.get('new_name', {})

            extracted_old = old_name_data.get('value', '') or ''
            extracted_new = new_name_data.get('value', '') or ''
            extraction_confidence = (
                (old_name_data.get('confidence', 0) or 0) +
                (new_name_data.get('confidence', 0) or 0)
            ) / 2

            logger.info(f"[{request_id}] LLM Extraction result: old='{extracted_old}', new='{extracted_new}', conf={extraction_confidence:.2f}")

            flags = list(state.get('flags', []))
            if not extracted_old and not extracted_new:
                flags.append("EXTRACTION_FAILED")
            elif not extracted_old or not extracted_new:
                flags.append("PARTIAL_EXTRACTION")

            return {
                "extracted_old_value": extracted_old,
                "extracted_new_value": extracted_new,
                "extraction_confidence": float(extraction_confidence),
                "extracted_fields": {
                    "old_name": old_name_data,
                    "new_name": new_name_data,
                    "extraction_notes": extraction_result.get('extraction_notes', ''),
                },
                "flags": flags,
                "current_step": "extractor_agent",
            }

        except Exception as e:
            logger.error(f"[{request_id}] Extractor agent error: {e}")
            return {
                "extracted_old_value": "",
                "extracted_new_value": "",
                "extraction_confidence": 0.0,
                "flags": state.get('flags', []) + ["EXTRACTION_FAILED"],
                "errors": state.get('errors', []) + [f"Extraction failed: {str(e)}"],
                "current_step": "extractor_agent",
            }

    async def forgery_node(state: SupervisorState) -> Dict[str, Any]:
        """Run Forgery agent to detect tampering."""
        request_id = state.get('request_id', 'unknown')
        document_path = state.get('document_path', '')

        update_step_in_db(request_id, "forgery")
        logger.info(f"[{request_id}] Supervisor: Delegating to Forgery agent")

        try:
            task = f"""{FORGERY_AGENT_PROMPT}

Task: Analyze this document for signs of forgery.
Document path: {document_path}

Use your tools to perform comprehensive forgery analysis."""

            result = await forgery_agent.ainvoke({
                "messages": [HumanMessage(content=task)]
            })

            # Fallback: use tools directly
            from app.agents.specialized.forgery_tools import (
                analyze_document_metadata,
                run_error_level_analysis,
                analyze_font_consistency,
                calculate_forgery_score,
            )

            metadata_result = analyze_document_metadata.invoke(document_path)
            ela_result = run_error_level_analysis.invoke(document_path)
            font_result = analyze_font_consistency.invoke(document_path)

            score_result = calculate_forgery_score.invoke({
                "metadata_score": metadata_result.get('score', 0.7),
                "ela_score": ela_result.get('score', 0.7),
                "font_score": font_result.get('score', 0.7),
            })

            logger.info(f"[{request_id}] Forgery analysis: score={score_result.get('overall_score', 0):.2f}, result={score_result.get('result')}")

            flags = list(state.get('flags', []))
            flags.extend(score_result.get('flags', []))

            return {
                "forgery_score": float(score_result.get('overall_score', 0.7)),
                "forgery_result": score_result.get('result', 'FLAG'),
                "forgery_details": {
                    "metadata": metadata_result,
                    "ela": ela_result,
                    "font": font_result,
                    "combined": score_result,
                    "assessment": score_result.get('assessment', ''),
                },
                "flags": flags,
                "current_step": "forgery_agent",
            }

        except Exception as e:
            logger.error(f"[{request_id}] Forgery agent error: {e}")
            return {
                "forgery_score": 0.7,
                "forgery_result": "FLAG",
                "flags": state.get('flags', []) + ["FORGERY_CHECK_ERROR"],
                "errors": state.get('errors', []) + [f"Forgery detection failed: {str(e)}"],
                "current_step": "forgery_agent",
            }

    async def scorer_node(state: SupervisorState) -> Dict[str, Any]:
        """Run Scorer agent to calculate final scores."""
        request_id = state.get('request_id', 'unknown')

        update_step_in_db(request_id, "scorer")
        logger.info(f"[{request_id}] Supervisor: Delegating to Scorer agent")

        try:
            from app.agents.specialized.scorer_tools import (
                calculate_name_similarity,
                calculate_overall_score,
                determine_risk_tier,
                generate_name_match_flags,
            )

            old_similarity = calculate_name_similarity.invoke({
                "extracted_name": state.get('extracted_old_value', ''),
                "expected_name": state.get('requested_old_value', ''),
            })

            new_similarity = calculate_name_similarity.invoke({
                "extracted_name": state.get('extracted_new_value', ''),
                "expected_name": state.get('requested_new_value', ''),
            })

            overall = calculate_overall_score.invoke({
                "old_name_score": old_similarity.get('score', 0.0),
                "new_name_score": new_similarity.get('score', 0.0),
                "forgery_score": state.get('forgery_score', 0.7),
                "ocr_confidence": state.get('ocr_confidence', 0.8),
                "extraction_confidence": state.get('extraction_confidence', 0.8),
            })

            name_flags = generate_name_match_flags.invoke({
                "old_score": old_similarity.get('score', 0.0),
                "new_score": new_similarity.get('score', 0.0),
            })

            flags = list(state.get('flags', []))
            flags.extend(name_flags.get('flags', []))

            risk = determine_risk_tier.invoke({
                "overall_score": overall.get('overall_score', 0.0),
                "flags": flags,
            })

            return {
                "old_name_match_score": float(old_similarity.get('score', 0.0)),
                "new_name_match_score": float(new_similarity.get('score', 0.0)),
                "overall_score": float(overall.get('overall_score', 0.0)),
                "risk_tier": risk.get('risk_tier', 'HIGH'),
                "ai_recommendation": risk.get('recommendation', 'MANUAL_REVIEW'),
                "flags": flags,
                "current_step": "scorer_agent",
            }

        except Exception as e:
            logger.error(f"[{request_id}] Scorer agent error: {e}")
            return {
                "overall_score": 0.0,
                "risk_tier": "HIGH",
                "ai_recommendation": "MANUAL_REVIEW",
                "errors": state.get('errors', []) + [f"Scoring failed: {str(e)}"],
                "current_step": "scorer_agent",
            }

    async def summary_node(state: SupervisorState) -> Dict[str, Any]:
        """Generate final summary."""
        request_id = state.get('request_id', 'unknown')

        update_step_in_db(request_id, "summary")
        logger.info(f"[{request_id}] Supervisor: Generating summary")

        # Use LLM to generate a comprehensive, actionable summary
        try:
            from langchain_anthropic import ChatAnthropic
            from app.config import settings

            llm = ChatAnthropic(
                model=settings.LLM_MODEL,
                temperature=0,
                max_tokens=1000,
                api_key=settings.ANTHROPIC_API_KEY,
                base_url=settings.ANTHROPIC_BASE_URL or None,
            )

            overall_score = state.get('overall_score', 0.0)
            risk_tier = state.get('risk_tier', 'HIGH')
            recommendation = state.get('ai_recommendation', 'MANUAL_REVIEW')
            flags = state.get('flags', [])

            prompt = f"""Generate a concise summary for a human reviewer about this name change verification request.

REQUEST DETAILS:
- Customer's current name: {state.get('requested_old_value', 'N/A')}
- Requested new name: {state.get('requested_new_value', 'N/A')}
- Document type: {state.get('document_type', 'N/A')}

VERIFICATION RESULTS:
- Name in document: {state.get('extracted_new_value', 'Not found')}
- Name match confidence: {state.get('new_name_match_score', 0):.0%}
- Document authenticity: {state.get('forgery_score', 0):.0%} ({state.get('forgery_result', 'N/A')})
- OCR quality: {state.get('ocr_confidence', 0):.0%}
- Overall confidence: {overall_score:.0%}
- Risk tier: {risk_tier}
- AI recommendation: {recommendation}
- Flags: {', '.join(flags) if flags else 'None'}

EXTRACTION NOTES:
{state.get('extracted_fields', {}).get('extraction_notes', 'N/A')}

Write a 2-3 sentence summary that:
1. States whether the document supports the name change
2. Highlights any concerns or flags
3. Gives a clear recommendation

Keep it professional and concise. Do not use markdown formatting."""

            response = llm.invoke(prompt)
            ai_summary = response.content.strip()

        except Exception as e:
            logger.warning(f"[{request_id}] LLM summary generation failed: {e}, using fallback")
            # Fallback to simple summary
            overall_score = state.get('overall_score', 0.0)
            risk_tier = state.get('risk_tier', 'HIGH')
            flags = state.get('flags', [])

            summary_parts = []
            summary_parts.append(f"Overall confidence: {overall_score:.0%}")
            summary_parts.append(f"Risk tier: {risk_tier}")

            if state.get('extracted_new_value'):
                summary_parts.append(f"Document name: '{state.get('extracted_new_value')}'")

            if flags:
                summary_parts.append(f"Flags: {', '.join(flags)}")

            ai_summary = " | ".join(summary_parts)

        return {
            "ai_summary": ai_summary,
            "processing_completed_at": datetime.utcnow().isoformat(),
            "current_step": "complete",
        }

    def route_after_validation(state: SupervisorState) -> str:
        """Route based on validation result."""
        request_id = state.get('request_id', 'unknown')
        validation_passed = state.get('validation_passed', False)
        logger.info(f"[{request_id}] Routing after validation: passed={validation_passed}")
        if validation_passed:
            logger.info(f"[{request_id}] Routing to OCR agent")
            return "continue"
        logger.info(f"[{request_id}] Validation failed, ending pipeline")
        return "end"

    # Build the graph
    graph = StateGraph(SupervisorState)

    # Add nodes
    graph.add_node("validation", validation_node)
    graph.add_node("ocr_agent", ocr_node)
    graph.add_node("classifier_agent", classifier_node)
    graph.add_node("extractor_agent", extractor_node)
    graph.add_node("forgery_agent", forgery_node)
    graph.add_node("scorer_agent", scorer_node)
    graph.add_node("summary", summary_node)

    # Set entry point
    graph.set_entry_point("validation")

    # Add edges
    graph.add_conditional_edges(
        "validation",
        route_after_validation,
        {
            "continue": "ocr_agent",
            "end": END,
        }
    )

    # Sequential flow through agents
    graph.add_edge("ocr_agent", "classifier_agent")
    graph.add_edge("classifier_agent", "extractor_agent")
    graph.add_edge("extractor_agent", "forgery_agent")
    graph.add_edge("forgery_agent", "scorer_agent")
    graph.add_edge("scorer_agent", "summary")
    graph.add_edge("summary", END)

    return graph.compile()


class SupervisorPipeline:
    """
    Supervisor-based document processing pipeline.

    Uses a supervisor LangGraph that orchestrates specialized worker agents.
    """

    def __init__(self):
        """Initialize the pipeline."""
        self.graph = create_supervisor_graph()
        logger.info("Supervisor pipeline initialized with worker agents")

    async def process(
        self,
        request_id: str,
        customer_id: str,
        change_type: str,
        document_type: str,
        requested_old_value: str,
        requested_new_value: str,
        document_path: str,
    ) -> Dict[str, Any]:
        """
        Process a document through the supervisor pipeline.

        Args:
            request_id: The request ID
            customer_id: Customer ID
            change_type: Type of change
            document_type: Type of document
            requested_old_value: Current value
            requested_new_value: New value requested
            document_path: Path to document

        Returns:
            Final processing state
        """
        logger.info(f"[{request_id}] Starting supervisor pipeline")

        initial_state = {
            "request_id": request_id,
            "customer_id": customer_id,
            "change_type": change_type,
            "document_type": document_type,
            "requested_old_value": requested_old_value,
            "requested_new_value": requested_new_value,
            "document_path": document_path,
            "flags": [],
            "errors": [],
            "llm_calls": [],
            "processing_started_at": datetime.utcnow().isoformat(),
        }

        try:
            final_state = await self.graph.ainvoke(initial_state)
            logger.info(f"[{request_id}] Supervisor pipeline completed")
            logger.info(f"[{request_id}] Final state keys: {list(final_state.keys())}")
            logger.info(f"[{request_id}] Current step: {final_state.get('current_step')}")
            logger.info(f"[{request_id}] Errors: {final_state.get('errors', [])}")
            return final_state

        except Exception as e:
            logger.error(f"[{request_id}] Supervisor pipeline failed: {e}")
            initial_state['errors'].append(str(e))
            initial_state['current_step'] = 'failed'
            return initial_state
