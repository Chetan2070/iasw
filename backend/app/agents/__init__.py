"""
Agents Module - LangGraph Document Processing Pipeline

This module implements the AI-powered document verification system using LangGraph.
It supports two architectures:
1. Linear Pipeline: Sequential nodes with conditional routing
2. Supervisor-Agent: Orchestrated specialized agents (default)

Key Components:
- state.py: ProcessingState TypedDict for pipeline state
- graph.py: Main pipeline definition and DocumentProcessingPipeline class
- prompts/: Centralized AI prompts for all agents
- nodes/: Individual processing nodes (OCR, classifier, extractor, forgery, scorer, summary)
- specialized/: ReAct agents and supervisor for agent-based architecture
"""

from app.agents.state import ProcessingState, create_initial_state
from app.agents.graph import pipeline, DocumentProcessingPipeline

__all__ = [
    "ProcessingState",
    "create_initial_state",
    "pipeline",
    "DocumentProcessingPipeline",
]
