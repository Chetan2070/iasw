"""
Tools for Extractor Agent

Provides tools for extracting structured fields from documents using LLM.
"""

import json
import logging
from typing import List
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from app.config import settings

logger = logging.getLogger(__name__)


def get_llm():
    """Get LLM instance for extraction."""
    return ChatAnthropic(
        model=settings.LLM_MODEL,
        temperature=0,
        max_tokens=2000,
        api_key=settings.ANTHROPIC_API_KEY,
        base_url=settings.ANTHROPIC_BASE_URL or None,
    )


@tool
def extract_names_with_llm(text: str, document_type: str, requested_old: str, requested_new: str) -> dict:
    """
    Extract the name from document and validate against the requested new name.

    The verification logic:
    - OLD NAME: Customer's current name in our database (provided as requested_old)
    - NEW NAME: The name that appears in the submitted document (extracted from text)
    - VALIDATION: Check if extracted name matches the requested_new value

    For a marriage certificate: Extract the person's name as recorded in the certificate.
    This should match the customer's requested NEW name.

    Args:
        text: OCR extracted text from the document
        document_type: Type of document (e.g., MARRIAGE_CERTIFICATE, DEED_POLL)
        requested_old: Customer's current name in our system (what they're changing FROM)
        requested_new: Customer's requested new name (what they want to change TO)

    Returns:
        Dict with extracted name, confidence scores, and validation
    """
    llm = get_llm()

    prompt = f"""You are an expert at extracting names from legal documents for name change verification.

DOCUMENT TYPE: {document_type}

VERIFICATION CONTEXT:
- Customer's CURRENT name in our system: {requested_old}
- Customer's REQUESTED new name: {requested_new}
- We need to verify the document supports this name change

YOUR TASK:
1. Find the person's name AS IT APPEARS in this document
2. For a MARRIAGE_CERTIFICATE: Extract the bride/wife's name as recorded
3. For a DEED_POLL or GAZETTE: Extract both the old and new names if present
4. For other documents: Extract the primary person's name

The extracted name from the document should match or be very similar to the customer's REQUESTED NEW NAME ({requested_new}).

DOCUMENT TEXT:
{text[:6000]}

Respond in JSON format only:
{{
    "document_name": {{
        "value": "the name as it appears in the document",
        "confidence": 0.0-1.0,
        "source_text": "exact text snippet where you found this name",
        "reasoning": "why you identified this as the relevant name"
    }},
    "matches_requested_new": {{
        "match": true/false,
        "similarity_assessment": "exact_match / close_match / partial_match / no_match",
        "explanation": "explain how the document name compares to '{requested_new}'"
    }},
    "extraction_notes": "any observations about the document or name verification"
}}"""

    try:
        response = llm.invoke(prompt)
        content = response.content

        # Parse JSON from response
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            result = json.loads(content[json_start:json_end])

            # Map to expected format for downstream processing
            doc_name = result.get('document_name', {})
            match_info = result.get('matches_requested_new', {})

            extracted_name = doc_name.get('value', '')
            confidence = doc_name.get('confidence', 0.0)

            # Determine if this is a good match
            is_match = match_info.get('match', False)
            similarity = match_info.get('similarity_assessment', 'no_match')

            # Adjust confidence based on match quality
            if similarity == 'exact_match':
                confidence = max(confidence, 0.95)
            elif similarity == 'close_match':
                confidence = max(confidence, 0.85)
            elif similarity == 'partial_match':
                confidence = min(confidence, 0.7)

            logger.info(f"LLM extraction: name='{extracted_name}', matches_requested={is_match}, similarity={similarity}")

            return {
                "old_name": {
                    "value": requested_old,  # Old name comes from database/request
                    "confidence": 1.0,  # We trust the database value
                    "source_text": "Customer's current name in system",
                    "reasoning": "Provided by customer as their current registered name"
                },
                "new_name": {
                    "value": extracted_name,
                    "confidence": confidence,
                    "source_text": doc_name.get('source_text', ''),
                    "reasoning": doc_name.get('reasoning', '')
                },
                "validation": {
                    "matches_requested": is_match,
                    "similarity": similarity,
                    "explanation": match_info.get('explanation', '')
                },
                "extraction_notes": result.get('extraction_notes', '')
            }
        else:
            logger.warning("Could not parse JSON from LLM response")
            return {
                "old_name": {"value": requested_old, "confidence": 1.0, "reasoning": "From database"},
                "new_name": {"value": None, "confidence": 0.0, "reasoning": "Failed to parse LLM response"},
                "extraction_notes": "LLM response parsing failed"
            }

    except Exception as e:
        logger.error(f"LLM extraction error: {e}")
        return {
            "old_name": {"value": requested_old, "confidence": 1.0, "reasoning": "From database"},
            "new_name": {"value": None, "confidence": 0.0, "reasoning": f"Error: {str(e)}"},
            "extraction_notes": f"Extraction failed: {str(e)}"
        }


@tool
def search_for_names(text: str, search_patterns: List[str]) -> dict:
    """
    Search document text for name patterns using simple text matching.
    This is a fallback method - prefer extract_names_with_llm for better accuracy.

    Args:
        text: OCR extracted text
        search_patterns: Optional list of specific names to search for

    Returns:
        Dict with found names and their contexts
    """
    results = []

    # If specific names provided, search for them
    if search_patterns:
        for name in search_patterns:
            if name and name.lower() in text.lower():
                # Find the position and context
                pos = text.lower().find(name.lower())
                start = max(0, pos - 50)
                end = min(len(text), pos + len(name) + 50)
                context = text[start:end]

                results.append({
                    "name": name,
                    "found": True,
                    "context": context,
                    "position": pos,
                })

    return {
        "found_names": results,
        "count": len(results),
        "search_method": "text_match",
    }


@tool
def identify_name_roles(text: str, found_names: List[dict]) -> dict:
    """
    Identify which names are old/new names based on context.
    This is a legacy fallback - prefer extract_names_with_llm.

    Args:
        text: Full document text
        found_names: List of found names with their contexts

    Returns:
        Dict mapping names to their roles (old_name/new_name)
    """
    old_name_indicators = [
        "maiden name", "previous name", "old name", "former name",
        "bride's name", "previously known as", "formerly known as",
        "born as", "applicant name", "deponent"
    ]

    new_name_indicators = [
        "married name", "new name", "current name", "changed to",
        "now known as", "shall be known as", "assumed name",
        "name after marriage", "present name"
    ]

    old_name_candidates = []
    new_name_candidates = []

    for name_data in found_names:
        context_lower = name_data.get("context", "").lower()
        name = name_data.get("name", "")

        old_score = sum(1 for ind in old_name_indicators if ind in context_lower)
        new_score = sum(1 for ind in new_name_indicators if ind in context_lower)

        if old_score > new_score:
            old_name_candidates.append({
                "name": name,
                "confidence": min(0.9, 0.5 + (old_score * 0.15)),
                "indicators_found": [ind for ind in old_name_indicators if ind in context_lower],
                "context": name_data.get("context", ""),
            })
        elif new_score > old_score:
            new_name_candidates.append({
                "name": name,
                "confidence": min(0.9, 0.5 + (new_score * 0.15)),
                "indicators_found": [ind for ind in new_name_indicators if ind in context_lower],
                "context": name_data.get("context", ""),
            })

    best_old = max(old_name_candidates, key=lambda x: x["confidence"]) if old_name_candidates else None
    best_new = max(new_name_candidates, key=lambda x: x["confidence"]) if new_name_candidates else None

    return {
        "old_name": best_old,
        "new_name": best_new,
        "all_old_candidates": old_name_candidates,
        "all_new_candidates": new_name_candidates,
    }


@tool
def validate_extraction(old_name: str, new_name: str, requested_old: str, requested_new: str) -> dict:
    """
    Validate extracted names against requested names using fuzzy matching.

    Args:
        old_name: Extracted old name
        new_name: Extracted new name
        requested_old: Customer's current name
        requested_new: Customer's requested new name

    Returns:
        Validation results with match assessment
    """
    from jellyfish import jaro_winkler_similarity

    def normalize(s):
        return s.lower().strip() if s else ""

    old_similarity = jaro_winkler_similarity(
        normalize(old_name), normalize(requested_old)
    ) if old_name and requested_old else 0.0

    new_similarity = jaro_winkler_similarity(
        normalize(new_name), normalize(requested_new)
    ) if new_name and requested_new else 0.0

    flags = []
    if not old_name:
        flags.append("OLD_NAME_NOT_FOUND")
    elif old_similarity < 0.7:
        flags.append("OLD_NAME_MISMATCH")
    elif old_similarity < 0.85:
        flags.append("OLD_NAME_FUZZY_MATCH")

    if not new_name:
        flags.append("NEW_NAME_NOT_FOUND")
    elif new_similarity < 0.7:
        flags.append("NEW_NAME_MISMATCH")
    elif new_similarity < 0.85:
        flags.append("NEW_NAME_FUZZY_MATCH")

    return {
        "old_name_similarity": float(old_similarity),
        "new_name_similarity": float(new_similarity),
        "flags": flags,
        "extraction_quality": "good" if not flags else "needs_review" if len(flags) <= 2 else "poor",
    }
