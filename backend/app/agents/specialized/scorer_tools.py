"""
Tools for Scorer Agent

Provides tools for calculating confidence scores and risk assessment.
"""

import logging
from typing import List
from jellyfish import jaro_winkler_similarity

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def calculate_name_similarity(extracted_name: str, expected_name: str) -> dict:
    """
    Calculate similarity between extracted and expected names.

    Args:
        extracted_name: Name extracted from document
        expected_name: Name expected from customer request

    Returns:
        Similarity score and match assessment
    """
    if not extracted_name or not expected_name:
        return {
            "score": 0.0,
            "match_type": "missing",
            "extracted": extracted_name or "",
            "expected": expected_name or "",
        }

    extracted_normalized = extracted_name.lower().strip()
    expected_normalized = expected_name.lower().strip()

    score = jaro_winkler_similarity(extracted_normalized, expected_normalized)

    if score >= 0.95:
        match_type = "exact"
    elif score >= 0.85:
        match_type = "high"
    elif score >= 0.7:
        match_type = "fuzzy"
    else:
        match_type = "mismatch"

    return {
        "score": float(score),
        "match_type": match_type,
        "extracted": extracted_name,
        "expected": expected_name,
    }


@tool
def calculate_overall_score(
    old_name_score: float,
    new_name_score: float,
    forgery_score: float,
    ocr_confidence: float,
    extraction_confidence: float
) -> dict:
    """
    Calculate weighted overall confidence score.

    Args:
        old_name_score: Old name match score (0-1)
        new_name_score: New name match score (0-1)
        forgery_score: Document authenticity score (0-1)
        ocr_confidence: OCR quality score (0-1)
        extraction_confidence: Extraction quality score (0-1)

    Returns:
        Overall score with component breakdown
    """
    weights = {
        "name_match": 0.40,
        "doc_authenticity": 0.30,
        "ocr_confidence": 0.15,
        "extraction_confidence": 0.15,
    }

    avg_name_match = (old_name_score + new_name_score) / 2

    overall = (
        avg_name_match * weights["name_match"] +
        forgery_score * weights["doc_authenticity"] +
        ocr_confidence * weights["ocr_confidence"] +
        extraction_confidence * weights["extraction_confidence"]
    )

    return {
        "overall_score": float(overall),
        "components": {
            "avg_name_match": float(avg_name_match),
            "old_name_score": float(old_name_score),
            "new_name_score": float(new_name_score),
            "forgery_score": float(forgery_score),
            "ocr_confidence": float(ocr_confidence),
            "extraction_confidence": float(extraction_confidence),
        },
        "weights": weights,
    }


@tool
def determine_risk_tier(overall_score: float, flags: List[str]) -> dict:
    """
    Determine risk tier based on score and flags.

    Args:
        overall_score: Overall confidence score (0-1)
        flags: List of flags from processing

    Returns:
        Risk tier and recommendation
    """
    major_flags = [
        "FORGERY_FLAG", "DOC_TYPE_MISMATCH", "EXTRACTION_FAILED",
        "OLD_NAME_MISMATCH", "NEW_NAME_MISMATCH"
    ]
    has_major_flag = any(f in flags for f in major_flags)

    if overall_score >= 0.9 and not has_major_flag:
        risk_tier = "LOW"
        recommendation = "APPROVE"
        reasoning = "High confidence, no major issues"
    elif overall_score >= 0.7 and not has_major_flag:
        risk_tier = "MEDIUM"
        recommendation = "MANUAL_REVIEW"
        reasoning = "Moderate confidence, review recommended"
    else:
        risk_tier = "HIGH"
        recommendation = "REJECT" if overall_score < 0.5 else "MANUAL_REVIEW"
        if has_major_flag:
            reasoning = f"Major flags present: {[f for f in flags if f in major_flags]}"
        else:
            reasoning = "Low confidence score"

    return {
        "risk_tier": risk_tier,
        "recommendation": recommendation,
        "reasoning": reasoning,
        "has_major_flags": has_major_flag,
        "major_flags_found": [f for f in flags if f in major_flags],
    }


@tool
def generate_name_match_flags(old_score: float, new_score: float) -> dict:
    """
    Generate flags based on name match scores.

    Args:
        old_score: Old name match score
        new_score: New name match score

    Returns:
        List of flags based on match quality
    """
    flags = []

    if old_score < 0.7:
        flags.append("OLD_NAME_MISMATCH")
    elif old_score < 0.85:
        flags.append("OLD_NAME_FUZZY_MATCH")

    if new_score < 0.7:
        flags.append("NEW_NAME_MISMATCH")
    elif new_score < 0.85:
        flags.append("NEW_NAME_FUZZY_MATCH")

    return {
        "flags": flags,
        "old_name_status": "mismatch" if old_score < 0.7 else "fuzzy" if old_score < 0.85 else "match",
        "new_name_status": "mismatch" if new_score < 0.7 else "fuzzy" if new_score < 0.85 else "match",
    }
