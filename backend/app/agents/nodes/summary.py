"""
Summary Agent Node

Generates human-readable summary and AI recommendation.
"""

import logging
import json
from typing import Dict, Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import ProcessingState
from app.config import settings

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = """You are a document verification summary agent for a banking name change system.
Generate a clear, professional summary for a human reviewer.

Your summary must:
1. Confirm whether the submitted document supports the name change request
2. Mention the key verification results (name match, document authenticity)
3. Highlight any flags or concerns that need attention
4. End with a clear recommendation

Write in 2-3 concise sentences. Be direct and factual. No markdown formatting."""


def determine_recommendation(state: ProcessingState) -> str:
    """
    Determine AI recommendation based on scores and flags.

    Logic:
        - APPROVE: score >= 85%, name match >= 95%, no HIGH flags, forgery PASS
        - REJECT: score < 60%, name match < 70%, or forgery FAIL, or doc mismatch
        - MANUAL_REVIEW: everything else
    """
    overall_score = state.get('overall_score', 0)
    old_match = state.get('old_name_match_score', 0)
    new_match = state.get('new_name_match_score', 0)
    min_name_match = min(old_match, new_match)
    forgery_result = state.get('forgery_result', 'FLAG')
    flags = state.get('flags', [])

    # REJECT conditions
    if overall_score < 0.60:
        return "REJECT"
    if min_name_match < 0.70:
        return "REJECT"
    if forgery_result == "FAIL":
        return "REJECT"
    if "DOC_TYPE_MISMATCH" in flags:
        return "REJECT"
    if "EXTRACTION_FAILED" in flags:
        return "REJECT"

    # APPROVE conditions
    if (overall_score >= 0.85 and
        min_name_match >= 0.95 and
        forgery_result == "PASS" and
        not any(f in flags for f in ["FORGERY_FLAG", "DOC_TYPE_MISMATCH", "EXTRACTION_FAILED"])):
        return "APPROVE"

    # Default to manual review
    return "MANUAL_REVIEW"


async def summary_node(state: ProcessingState) -> Dict[str, Any]:
    """
    Generates AI summary and recommendation for checker.

    Process:
        1. Determine recommendation based on scores/flags
        2. Generate human-readable summary using LLM
        3. Return summary and recommendation

    Input State:
        - All previous outputs (scores, flags, extracted fields)

    Output State Updates:
        - ai_summary: str
        - ai_recommendation: str
        - current_step: "summary"
    """
    request_id = state.get('request_id', 'unknown')

    logger.info(f"[{request_id}] Generating summary")

    try:
        # Determine recommendation first (rule-based)
        recommendation = determine_recommendation(state)

        # Initialize LLM with optional proxy
        llm_kwargs = {
            "model": settings.LLM_MODEL,
            "api_key": settings.ANTHROPIC_API_KEY,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": 512,
        }
        if settings.ANTHROPIC_BASE_URL:
            llm_kwargs["base_url"] = settings.ANTHROPIC_BASE_URL

        llm = ChatAnthropic(**llm_kwargs)

        # Build context for LLM
        context = f"""NAME CHANGE REQUEST VERIFICATION

Customer's current name: {state.get('requested_old_value', 'N/A')}
Customer's requested new name: {state.get('requested_new_value', 'N/A')}
Document type submitted: {state.get('document_type', 'Unknown')}

VERIFICATION RESULTS:
- Name extracted from document: {state.get('extracted_new_value', 'Not found')}
- Name match score: {state.get('new_name_match_score', 0):.0%}
- Document authenticity: {state.get('forgery_score', 0):.0%} ({state.get('forgery_result', 'Unknown')})
- OCR confidence: {state.get('ocr_confidence', 0):.0%}
- Overall confidence: {state.get('overall_score', 0):.0%}
- Risk tier: {state.get('risk_tier', 'Unknown')}
- Flags: {', '.join(state.get('flags', [])) or 'None'}

AI Recommendation: {recommendation}

Generate a 2-3 sentence summary for the human reviewer."""

        # Create messages
        messages = [
            SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
            HumanMessage(content=context)
        ]

        # Call LLM
        response = await llm.ainvoke(messages)
        summary = response.content.strip()

        # Remove any JSON formatting if present
        if summary.startswith('{'):
            try:
                result = json.loads(summary)
                summary = result.get('summary', summary)
            except json.JSONDecodeError:
                pass

        # Ensure recommendation is appended to summary
        if recommendation not in summary:
            summary = f"{summary} Recommendation: {recommendation}"

        # Track LLM call
        llm_calls = list(state.get('llm_calls', []))
        llm_calls.append({
            "node": "summary",
            "model": settings.LLM_MODEL,
            "input_tokens": len(context.split()),
            "output_tokens": len(summary.split()),
        })

        logger.info(f"[{request_id}] Summary generated - recommendation: {recommendation}")

        return {
            "ai_summary": summary,
            "ai_recommendation": recommendation,
            "llm_calls": llm_calls,
            "current_step": "summary",
        }

    except Exception as e:
        logger.error(f"[{request_id}] Summary generation failed: {str(e)}")

        # Generate better fallback summary
        recommendation = determine_recommendation(state)
        extracted_name = state.get('extracted_new_value', 'N/A')
        requested_new = state.get('requested_new_value', 'N/A')
        match_score = state.get('new_name_match_score', 0)
        forgery_result = state.get('forgery_result', 'Unknown')
        flags = state.get('flags', [])

        # Build a meaningful fallback summary
        if match_score >= 0.9 and forgery_result == "PASS":
            fallback_summary = (
                f"The submitted document contains the name '{extracted_name}' which matches the requested new name "
                f"with {match_score:.0%} confidence. Document authenticity verified ({forgery_result}). "
                f"Recommendation: {recommendation}."
            )
        elif match_score < 0.7:
            fallback_summary = (
                f"Name verification issue: Document shows '{extracted_name}' but customer requested '{requested_new}' "
                f"(match score: {match_score:.0%}). Manual review required. Recommendation: {recommendation}."
            )
        else:
            flag_text = f" Flags: {', '.join(flags)}." if flags else ""
            fallback_summary = (
                f"Document verification completed with {state.get('overall_score', 0):.0%} confidence. "
                f"Name match: {match_score:.0%}, Authenticity: {forgery_result}.{flag_text} "
                f"Recommendation: {recommendation}."
            )

        return {
            "ai_summary": fallback_summary,
            "ai_recommendation": recommendation,
            "errors": state.get('errors', []) + [f"Summary generation failed: {str(e)}"],
            "current_step": "summary",
        }
