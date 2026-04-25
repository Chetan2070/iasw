"""
Tools for Classifier Agent

Provides tools for document classification.
"""

import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

DOCUMENT_TYPES = [
    "MARRIAGE_CERTIFICATE",
    "GAZETTE_NOTIFICATION",
    "DEED_POLL",
    "COURT_ORDER",
    "UTILITY_BILL",
    "BIRTH_CERTIFICATE",
    "PASSPORT",
    "PAN_CARD",
    "CONSENT_FORM",
    "OTHER",
]

DOCUMENT_KEYWORDS = {
    "MARRIAGE_CERTIFICATE": [
        "marriage", "bride", "groom", "matrimony",
        "solemnized", "husband", "wife", "wedding", "registrar",
        "hindu marriage", "marriage registration", "spouse"
    ],
    "GAZETTE_NOTIFICATION": [
        "gazette", "notification", "government", "published",
        "hereby", "declare", "notification number", "official gazette"
    ],
    "DEED_POLL": [
        "deed poll", "deed of change", "renounce", "assume",
        "absolutely", "declare", "witness", "enrolled"
    ],
    "COURT_ORDER": [
        "court", "order", "judge", "petitioner", "decree",
        "directed", "hereby ordered", "plaintiff", "defendant"
    ],
    "UTILITY_BILL": [
        "bill", "electricity", "water", "gas", "utility",
        "account number", "due date", "amount payable", "meter"
    ],
    "BIRTH_CERTIFICATE": [
        "birth certificate", "born on", "child name", "parents name",
        "place of birth", "registration of birth", "live birth",
        "father name", "mother name"
    ],
    "PASSPORT": [
        "passport", "nationality", "travel document",
        "date of issue", "date of expiry", "place of issue",
        "passport number", "visa"
    ],
    "PAN_CARD": [
        "permanent account number", "pan", "income tax",
        "department", "government of india", "pan card"
    ],
    "CONSENT_FORM": [
        "consent", "authorize", "permission", "agree",
        "signature", "acknowledge", "i hereby consent"
    ],
}


@tool
def analyze_document_keywords(text: str) -> dict:
    """
    Analyze document text for classification keywords.

    Args:
        text: OCR extracted text from the document

    Returns:
        Dict with keyword matches for each document type
    """
    text_lower = text.lower()
    results = {}

    for doc_type, keywords in DOCUMENT_KEYWORDS.items():
        matches = []
        for keyword in keywords:
            if keyword.lower() in text_lower:
                matches.append(keyword)

        results[doc_type] = {
            "matches": matches,
            "match_count": len(matches),
            "total_keywords": len(keywords),
            "match_ratio": len(matches) / len(keywords) if keywords else 0,
        }

    return results


@tool
def determine_document_type(keyword_analysis: dict, declared_type: str) -> dict:
    """
    Determine the most likely document type based on keyword analysis.

    Args:
        keyword_analysis: Output from analyze_document_keywords
        declared_type: The document type declared by the user

    Returns:
        Classification result with confidence and match status
    """
    if not keyword_analysis:
        return {
            "detected_type": declared_type,
            "confidence": 0.5,
            "is_match": True,
            "reasoning": "No keyword analysis available, using declared type",
        }

    # Score each document type
    type_scores = []
    for doc_type, data in keyword_analysis.items():
        type_scores.append({
            "type": doc_type,
            "ratio": data["match_ratio"],
            "count": data["match_count"],
        })

    # Sort by ratio, then by count
    type_scores.sort(key=lambda x: (x["ratio"], x["count"]), reverse=True)

    if not type_scores or type_scores[0]["ratio"] < 0.2:
        return {
            "detected_type": "OTHER",
            "confidence": 0.4,
            "is_match": declared_type == "OTHER",
            "reasoning": "No strong keyword matches found",
            "keyword_matches": keyword_analysis,
        }

    best = type_scores[0]
    best_type = best["type"]
    best_ratio = best["ratio"]

    # If declared type is in top candidates (within 10% of best), prefer declared type
    declared_upper = declared_type.upper()
    for ts in type_scores[:3]:  # Check top 3
        if ts["type"].upper() == declared_upper:
            # If declared type is close to the best (within 20% ratio difference), use it
            if ts["ratio"] >= best_ratio * 0.8:
                best_type = declared_type
                best_ratio = ts["ratio"]
                break

    confidence = min(0.95, 0.5 + (best_ratio * 0.5))
    is_match = best_type.upper() == declared_upper

    return {
        "detected_type": best_type,
        "confidence": float(confidence),
        "is_match": is_match,
        "reasoning": f"Best match based on {keyword_analysis.get(best_type, {}).get('match_count', 0)} keyword matches",
        "keyword_matches": keyword_analysis.get(best_type, {}),
        "top_candidates": [ts["type"] for ts in type_scores[:3]],
    }


@tool
def check_classification_flags(detected_type: str, declared_type: str, confidence: float) -> dict:
    """
    Generate flags based on classification results.

    Args:
        detected_type: The classified document type
        declared_type: The user-declared document type
        confidence: Classification confidence score

    Returns:
        Dict with classification flags
    """
    flags = []

    if detected_type.upper() != declared_type.upper():
        flags.append("DOC_TYPE_MISMATCH")

    if confidence < 0.6:
        flags.append("DOC_TYPE_UNCERTAIN")
    elif confidence < 0.7:
        flags.append("DOC_TYPE_LOW_CONFIDENCE")

    return {
        "flags": flags,
        "has_mismatch": "DOC_TYPE_MISMATCH" in flags,
        "needs_review": len(flags) > 0,
    }
