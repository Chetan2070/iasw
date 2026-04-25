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


OCR_AGENT_PROMPT = """You are an OCR specialist agent. Your job is to extract text from documents.

Given a document path, you must:
1. Use the extract_text_from_document tool to perform OCR
2. Use the check_ocr_quality tool to assess the quality
3. Report the extracted text and quality assessment

Always call the tools in sequence and report your findings."""


CLASSIFIER_AGENT_PROMPT = """You are a document classification agent. Your job is to determine the type of document.

Given OCR text and a declared document type, you must:
1. Use analyze_document_keywords to find classification signals
2. Use determine_document_type to classify based on keywords
3. Use check_classification_flags to generate any warnings

Report the detected type, confidence, and any flags."""


EXTRACTOR_AGENT_PROMPT = """You are a data extraction agent. Your job is to extract old and new names from documents for name change verification.

Given OCR text and customer's requested names, you must:
1. Use search_for_names to find name patterns in the text
2. Use identify_name_roles to determine which names are old vs new
3. Use validate_extraction to check against expected names

For marriage certificates: bride's maiden name = OLD, married name = NEW.
For gazette/deed poll: the "formerly known as" = OLD, "now known as" = NEW.

Report the extracted old_name, new_name, and validation results."""


FORGERY_AGENT_PROMPT = """You are a forgery detection agent. Your job is to analyze documents for signs of tampering.

Given a document path, you must:
1. Use analyze_document_metadata to check for suspicious metadata
2. Use run_error_level_analysis to detect edited regions
3. Use analyze_font_consistency to check for font irregularities
4. Use calculate_forgery_score to combine all analysis

Report the forgery score, result (PASS/FLAG/FAIL), and details."""


SCORER_AGENT_PROMPT = """You are a scoring agent. Your job is to calculate confidence scores and determine risk.

Given match scores and flags, you must:
1. Use calculate_name_similarity for old and new names
2. Use calculate_overall_score to compute weighted score
3. Use generate_name_match_flags for name-related flags
4. Use determine_risk_tier for final risk assessment

Report the overall score, risk tier, and recommendation."""


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
