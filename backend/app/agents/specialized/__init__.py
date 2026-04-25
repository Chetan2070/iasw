"""
Specialized Agents Module

Implements a supervisor-worker architecture using LangGraph ReAct agents.
The supervisor orchestrates specialized worker agents for document processing.

Components:
- supervisor.py: SupervisorPipeline that orchestrates all agents
- worker_agents.py: Individual ReAct agents (OCR, Classifier, Extractor, Forgery, Scorer)
- *_tools.py: Tool functions that agents can call

Agent Tools:
- ocr_tools: Text extraction and quality assessment
- classifier_tools: Document type detection
- extractor_tools: Name extraction with LLM
- forgery_tools: Tampering detection (metadata, ELA, font analysis)
- scorer_tools: Confidence scoring and risk tier calculation
"""

from app.agents.specialized.supervisor import create_supervisor_graph, SupervisorPipeline
from app.agents.specialized.worker_agents import (
    create_ocr_agent,
    create_classifier_agent,
    create_extractor_agent,
    create_forgery_agent,
    create_scorer_agent,
    AGENT_CONFIGS,
)

__all__ = [
    "create_supervisor_graph",
    "SupervisorPipeline",
    "create_ocr_agent",
    "create_classifier_agent",
    "create_extractor_agent",
    "create_forgery_agent",
    "create_scorer_agent",
    "AGENT_CONFIGS",
]
