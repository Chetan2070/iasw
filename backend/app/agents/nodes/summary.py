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

SUMMARY_SYSTEM_PROMPT = """You are a document verification summary agent for a banking system.
Your task is to generate a clear, concise summary for a human checker who will review the request.

The summary should:
1. State what was verified and how
2. Highlight any flags or concerns
3. Include a clear recommendation: APPROVE, REJECT, or MANUAL_REVIEW

Keep the summary to 2-3 sentences maximum. Be direct and factual.

Format your response as JSON:
{
    "summary": "Your 2-3 sentence summary here",
    "recommendation": "APPROVE" or "REJECT" or "MANUAL_REVIEW",
    "key_points": ["point 1", "point 2"]
}"""


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
        context = f"""Document Type: {state.get('document_type', 'Unknown')}
Detected Type: {state.get('detected_document_type', 'Unknown')}
Classification Match: {state.get('classification_match', False)}

Requested Change:
- Old Name: {state.get('requested_old_value', 'N/A')}
- New Name: {state.get('requested_new_value', 'N/A')}

Extracted Values:
- Old Name: {state.get('extracted_old_value', 'N/A')}
- New Name: {state.get('extracted_new_value', 'N/A')}

Scores:
- Old Name Match: {state.get('old_name_match_score', 0):.0%}
- New Name Match: {state.get('new_name_match_score', 0):.0%}
- OCR Confidence: {state.get('ocr_confidence', 0):.0%}
- Document Authenticity: {state.get('forgery_score', 0):.0%}
- Overall Score: {state.get('overall_score', 0):.0%}

Forgery Check: {state.get('forgery_result', 'Unknown')}
Risk Tier: {state.get('risk_tier', 'Unknown')}
Flags: {', '.join(state.get('flags', [])) or 'None'}

Predetermined Recommendation: {recommendation}"""

        # Create messages
        messages = [
            SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
            HumanMessage(content=f"Generate a summary for this verification:\n\n{context}")
        ]

        # Call LLM
        response = await llm.ainvoke(messages)
        response_text = response.content

        # Parse JSON response
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response_text[json_start:json_end])
                summary = result.get('summary', '')
            else:
                summary = response_text.strip()
        except json.JSONDecodeError:
            summary = response_text.strip()

        # Ensure recommendation is appended to summary
        if recommendation not in summary:
            summary = f"{summary} Recommendation: {recommendation}"

        # Track LLM call
        llm_calls = list(state.get('llm_calls', []))
        llm_calls.append({
            "node": "summary",
            "model": settings.LLM_MODEL,
            "input_tokens": len(context.split()),
            "output_tokens": len(response_text.split()),
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

        # Generate fallback summary
        recommendation = determine_recommendation(state)
        fallback_summary = (
            f"Document verification completed. "
            f"Overall confidence: {state.get('overall_score', 0):.0%}. "
            f"Risk tier: {state.get('risk_tier', 'Unknown')}. "
            f"Recommendation: {recommendation}"
        )

        return {
            "ai_summary": fallback_summary,
            "ai_recommendation": recommendation,
            "errors": state.get('errors', []) + [f"Summary generation failed: {str(e)}"],
            "current_step": "summary",
        }
