"""
IASW Agent Prompts

Centralized repository of all AI prompts used in the document processing pipeline.
Organized by agent/node for easy maintenance and consistency.

This module provides:
- System prompts for each processing agent
- Field extraction schemas for different document types
- Helper functions to build dynamic prompts
"""

from app.agents.prompts.agent_prompts import (
    OCR_AGENT_PROMPT,
    CLASSIFIER_AGENT_PROMPT,
    EXTRACTOR_AGENT_PROMPT,
    FORGERY_AGENT_PROMPT,
    SCORER_AGENT_PROMPT,
)

from app.agents.prompts.node_prompts import (
    CLASSIFIER_SYSTEM_PROMPT,
    EXTRACTOR_SYSTEM_PROMPT,
    SUMMARY_SYSTEM_PROMPT,
    FORGERY_ANALYSIS_PROMPT,
    build_extraction_prompt,
    FIELD_SCHEMAS,
)

__all__ = [
    # Agent prompts (for ReAct agents)
    "OCR_AGENT_PROMPT",
    "CLASSIFIER_AGENT_PROMPT",
    "EXTRACTOR_AGENT_PROMPT",
    "FORGERY_AGENT_PROMPT",
    "SCORER_AGENT_PROMPT",
    # Node prompts (for direct LLM calls)
    "CLASSIFIER_SYSTEM_PROMPT",
    "EXTRACTOR_SYSTEM_PROMPT",
    "SUMMARY_SYSTEM_PROMPT",
    "FORGERY_ANALYSIS_PROMPT",
    "build_extraction_prompt",
    "FIELD_SCHEMAS",
]
