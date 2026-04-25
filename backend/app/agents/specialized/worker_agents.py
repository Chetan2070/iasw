"""
Worker Agents

Individual LangGraph ReAct agents for each processing step.
Each agent uses tools to accomplish its specific task.
"""

import logging
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from app.config import settings
from app.agents.prompts import (
    OCR_AGENT_PROMPT,
    CLASSIFIER_AGENT_PROMPT,
    EXTRACTOR_AGENT_PROMPT,
    FORGERY_AGENT_PROMPT,
    SCORER_AGENT_PROMPT,
)
from app.agents.specialized.ocr_tools import extract_text_from_document, check_ocr_quality
from app.agents.specialized.classifier_tools import (
    analyze_document_keywords,
    determine_document_type,
    check_classification_flags,
)
from app.agents.specialized.extractor_tools import (
    search_for_names,
    identify_name_roles,
    validate_extraction,
)
from app.agents.specialized.forgery_tools import (
    analyze_document_metadata,
    run_error_level_analysis,
    analyze_font_consistency,
    calculate_forgery_score,
)
from app.agents.specialized.scorer_tools import (
    calculate_name_similarity,
    calculate_overall_score,
    determine_risk_tier,
    generate_name_match_flags,
)

logger = logging.getLogger(__name__)


def get_llm():
    """Create LLM instance with configured settings."""
    llm_kwargs = {
        "model": settings.LLM_MODEL,
        "api_key": settings.ANTHROPIC_API_KEY,
        "temperature": settings.LLM_TEMPERATURE,
    }
    if settings.ANTHROPIC_BASE_URL:
        llm_kwargs["base_url"] = settings.ANTHROPIC_BASE_URL

    return ChatAnthropic(**llm_kwargs)


def create_ocr_agent():
    """Create the OCR ReAct agent."""
    llm = get_llm()
    tools = [extract_text_from_document, check_ocr_quality]
    return create_react_agent(llm, tools)


def create_classifier_agent():
    """Create the Classifier ReAct agent."""
    llm = get_llm()
    tools = [analyze_document_keywords, determine_document_type, check_classification_flags]
    return create_react_agent(llm, tools)


def create_extractor_agent():
    """Create the Extractor ReAct agent."""
    llm = get_llm()
    tools = [search_for_names, identify_name_roles, validate_extraction]
    return create_react_agent(llm, tools)


def create_forgery_agent():
    """Create the Forgery Detection ReAct agent."""
    llm = get_llm()
    tools = [
        analyze_document_metadata,
        run_error_level_analysis,
        analyze_font_consistency,
        calculate_forgery_score,
    ]
    return create_react_agent(llm, tools)


def create_scorer_agent():
    """Create the Scorer ReAct agent."""
    llm = get_llm()
    tools = [
        calculate_name_similarity,
        calculate_overall_score,
        determine_risk_tier,
        generate_name_match_flags,
    ]
    return create_react_agent(llm, tools)


# Agent configurations for the supervisor
AGENT_CONFIGS = {
    "ocr_agent": {
        "create_fn": create_ocr_agent,
        "prompt": OCR_AGENT_PROMPT,
        "description": "Extracts text from documents using OCR",
    },
    "classifier_agent": {
        "create_fn": create_classifier_agent,
        "prompt": CLASSIFIER_AGENT_PROMPT,
        "description": "Classifies document type",
    },
    "extractor_agent": {
        "create_fn": create_extractor_agent,
        "prompt": EXTRACTOR_AGENT_PROMPT,
        "description": "Extracts old/new names from documents",
    },
    "forgery_agent": {
        "create_fn": create_forgery_agent,
        "prompt": FORGERY_AGENT_PROMPT,
        "description": "Detects document forgery/tampering",
    },
    "scorer_agent": {
        "create_fn": create_scorer_agent,
        "prompt": SCORER_AGENT_PROMPT,
        "description": "Calculates scores and risk tier",
    },
}
