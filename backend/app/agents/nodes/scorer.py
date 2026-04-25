"""
Confidence Scorer Node

Calculates confidence scores and determines risk tier.
"""

import logging
from typing import Dict, Any, List

from jellyfish import jaro_winkler_similarity

from app.agents.state import ProcessingState
from app.config import settings

logger = logging.getLogger(__name__)


def calculate_name_match(extracted: str, expected: str) -> float:
    """
    Calculate similarity between extracted and expected names.

    Uses Jaro-Winkler similarity which is good for names.

    Args:
        extracted: Name extracted from document
        expected: Name expected (from request)

    Returns:
        Similarity score from 0.0 to 1.0
    """
    if not extracted or not expected:
        return 0.0

    # Normalize names for comparison
    extracted_normalized = extracted.lower().strip()
    expected_normalized = expected.lower().strip()

    # Calculate Jaro-Winkler similarity
    score = jaro_winkler_similarity(extracted_normalized, expected_normalized)

    return score


async def scorer_node(state: ProcessingState) -> Dict[str, Any]:
    """
    Calculates confidence scores and determines risk tier.

    Score Components:
        - Name Match (40%): Jaro-Winkler similarity for old + new names
        - Document Authenticity (30%): Forgery score
        - OCR Confidence (15%): OCR quality
        - Extraction Confidence (15%): LLM extraction quality

    Risk Tier Classification:
        - LOW: score >= 90%, no major flags
        - MEDIUM: score 70-90%, or minor flags
        - HIGH: score < 70%, or major flags

    Input State:
        - extracted_old_value, extracted_new_value
        - requested_old_value, requested_new_value
        - forgery_score
        - ocr_confidence
        - extraction_confidence
        - flags

    Output State Updates:
        - old_name_match_score: float
        - new_name_match_score: float
        - field_scores: List[dict]
        - overall_score: float
        - risk_tier: str
        - flags: may add NAME_MISMATCH flag
        - current_step: "scorer"
    """
    request_id = state.get('request_id', 'unknown')

    logger.info(f"[{request_id}] Calculating confidence scores")

    # Get values
    extracted_old = state.get('extracted_old_value', '')
    extracted_new = state.get('extracted_new_value', '')
    requested_old = state.get('requested_old_value', '')
    requested_new = state.get('requested_new_value', '')
    forgery_score = state.get('forgery_score', 0.7)
    ocr_confidence = state.get('ocr_confidence', 0.8)
    extraction_confidence = state.get('extraction_confidence', 0.8)

    # Calculate name match scores
    old_name_match_score = calculate_name_match(extracted_old, requested_old)
    new_name_match_score = calculate_name_match(extracted_new, requested_new)

    # Average name match score
    avg_name_match = (old_name_match_score + new_name_match_score) / 2

    # Build field scores list
    field_scores = [
        {
            "field": "old_name",
            "extracted": extracted_old,
            "expected": requested_old,
            "score": old_name_match_score,
            "method": "jaro_winkler",
        },
        {
            "field": "new_name",
            "extracted": extracted_new,
            "expected": requested_new,
            "score": new_name_match_score,
            "method": "jaro_winkler",
        },
    ]

    # Calculate weighted overall score
    overall_score = (
        avg_name_match * settings.WEIGHT_NAME_MATCH +
        forgery_score * settings.WEIGHT_DOC_AUTHENTICITY +
        ocr_confidence * settings.WEIGHT_OCR_CONFIDENCE +
        extraction_confidence * settings.WEIGHT_EXTRACTION_CONFIDENCE
    )

    # Update flags
    flags = list(state.get('flags', []))

    # Add name mismatch flags
    if old_name_match_score < settings.NAME_MATCH_LOW_THRESHOLD:
        flags.append("OLD_NAME_MISMATCH")
    elif old_name_match_score < settings.NAME_MATCH_HIGH_THRESHOLD:
        flags.append("OLD_NAME_FUZZY_MATCH")

    if new_name_match_score < settings.NAME_MATCH_LOW_THRESHOLD:
        flags.append("NEW_NAME_MISMATCH")
    elif new_name_match_score < settings.NAME_MATCH_HIGH_THRESHOLD:
        flags.append("NEW_NAME_FUZZY_MATCH")

    # Determine risk tier
    major_flags = [
        "FORGERY_FLAG", "DOC_TYPE_MISMATCH", "EXTRACTION_FAILED",
        "OLD_NAME_MISMATCH", "NEW_NAME_MISMATCH"
    ]
    has_major_flag = any(f in flags for f in major_flags)

    if overall_score >= settings.RISK_LOW_THRESHOLD and not has_major_flag:
        risk_tier = "LOW"
    elif overall_score >= settings.RISK_MEDIUM_THRESHOLD and not has_major_flag:
        risk_tier = "MEDIUM"
    else:
        risk_tier = "HIGH"

    logger.info(
        f"[{request_id}] Scoring complete - "
        f"overall: {overall_score:.2f}, "
        f"old_match: {old_name_match_score:.2f}, "
        f"new_match: {new_name_match_score:.2f}, "
        f"risk: {risk_tier}"
    )

    # Ensure all values are native Python types (not numpy)
    return {
        "old_name_match_score": float(old_name_match_score),
        "new_name_match_score": float(new_name_match_score),
        "field_scores": [
            {**fs, "score": float(fs["score"])} for fs in field_scores
        ],
        "overall_score": float(overall_score),
        "risk_tier": risk_tier,
        "flags": flags,
        "current_step": "scorer",
    }
