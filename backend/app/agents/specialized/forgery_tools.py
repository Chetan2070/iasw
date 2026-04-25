"""
Tools for Forgery Detection Agent

Provides tools for detecting document tampering through multiple analysis layers:

1. METADATA ANALYSIS
   - Examines PDF/image metadata for suspicious editing software
   - Checks creation vs modification dates
   - Detects tools commonly used for document manipulation (Photoshop, GIMP, etc.)

2. ERROR LEVEL ANALYSIS (ELA)
   - Re-saves image at known quality and compares to original
   - Edited regions show different compression artifacts
   - Higher variance in difference = potential tampering

3. FONT CONSISTENCY
   - Analyzes fonts used throughout the document
   - Legitimate documents typically use 1-3 consistent fonts
   - Many different fonts may indicate copy-paste from multiple sources
"""

import os
import hashlib
import logging
from PIL import Image

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def analyze_document_metadata(file_path: str) -> dict:
    """
    Analyze document metadata for suspicious patterns.

    Args:
        file_path: Path to the document file

    Returns:
        Metadata analysis results with authenticity score
    """
    details = {}
    score = 1.0

    try:
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.pdf':
            import fitz
            doc = fitz.open(file_path)
            metadata = doc.metadata

            details['producer'] = metadata.get('producer', '')
            details['creator'] = metadata.get('creator', '')
            details['creation_date'] = metadata.get('creationDate', '')
            details['mod_date'] = metadata.get('modDate', '')

            suspicious_producers = ['photoshop', 'canva', 'gimp', 'paint']
            producer_lower = details['producer'].lower()
            if any(sp in producer_lower for sp in suspicious_producers):
                score -= 0.3
                details['warning'] = 'Suspicious producer software detected'

            if details['mod_date'] and details['creation_date']:
                if details['mod_date'] != details['creation_date']:
                    score -= 0.1
                    details['note'] = 'Document was modified after creation'

            doc.close()

        elif ext in ['.jpg', '.jpeg', '.png']:
            from PIL.ExifTags import TAGS

            img = Image.open(file_path)
            exif_data = img._getexif()

            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag in ['Software', 'ProcessingSoftware']:
                        details[tag] = str(value)
                        if any(sp in str(value).lower() for sp in ['photoshop', 'gimp']):
                            score -= 0.2

            img.close()

    except Exception as e:
        logger.warning(f"Metadata analysis error: {e}")
        details['error'] = str(e)

    return {
        "score": max(0.0, float(score)),
        "details": details,
        "layer": "metadata",
    }


@tool
def run_error_level_analysis(file_path: str) -> dict:
    """
    Perform Error Level Analysis (ELA) to detect edited regions.

    Args:
        file_path: Path to the document file

    Returns:
        ELA results with tampering score
    """
    details = {}

    try:
        import numpy as np

        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.pdf':
            import fitz
            doc = fitz.open(file_path)
            page = doc[0]
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
        else:
            img = Image.open(file_path).convert('RGB')

        temp_path = '/tmp/ela_temp.jpg'
        img.save(temp_path, 'JPEG', quality=90)

        resaved = Image.open(temp_path)

        original_array = np.array(img, dtype=np.float32)
        resaved_array = np.array(resaved, dtype=np.float32)

        diff = np.abs(original_array - resaved_array)
        avg_diff = np.mean(diff)
        max_diff = np.max(diff)
        std_diff = np.std(diff)

        score = 1.0 - min(std_diff / 50.0, 1.0)

        details['avg_difference'] = float(avg_diff)
        details['max_difference'] = float(max_diff)
        details['std_difference'] = float(std_diff)

        os.remove(temp_path)
        resaved.close()
        img.close()

    except Exception as e:
        logger.warning(f"ELA analysis error: {e}")
        details['error'] = str(e)
        score = 0.7

    return {
        "score": max(0.0, min(1.0, float(score))),
        "details": details,
        "layer": "ela",
    }


@tool
def analyze_font_consistency(file_path: str) -> dict:
    """
    Analyze font consistency in the document.

    Args:
        file_path: Path to the document file

    Returns:
        Font analysis results with consistency score
    """
    details = {}
    score = 0.85

    try:
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.pdf':
            import fitz
            doc = fitz.open(file_path)

            fonts_used = set()
            for page in doc:
                font_list = page.get_fonts()
                for font in font_list:
                    fonts_used.add(font[3])

            details['fonts_found'] = list(fonts_used)
            details['font_count'] = len(fonts_used)

            if len(fonts_used) > 5:
                score -= 0.2
                details['warning'] = 'Multiple fonts detected'
            elif len(fonts_used) <= 2:
                score = 0.95

            doc.close()

        else:
            details['note'] = 'Font analysis limited for images'
            score = 0.8

    except Exception as e:
        logger.warning(f"Font analysis error: {e}")
        details['error'] = str(e)

    return {
        "score": max(0.0, min(1.0, float(score))),
        "details": details,
        "layer": "font",
    }


@tool
def calculate_forgery_score(metadata_score: float, ela_score: float, font_score: float) -> dict:
    """
    Calculate overall forgery score from individual layer scores.

    Scoring interpretation:
    - 0.8-1.0: PASS - Document appears authentic, no signs of tampering
    - 0.6-0.8: FLAG - Some indicators need review, proceed with caution
    - 0.0-0.6: FAIL - Significant signs of tampering detected

    Args:
        metadata_score: Score from metadata analysis (0-1, higher = more authentic)
        ela_score: Score from ELA analysis (0-1, higher = more authentic)
        font_score: Score from font analysis (0-1, higher = more authentic)

    Returns:
        Combined forgery assessment with explanation
    """
    weights = {
        'metadata': 0.25,
        'ela': 0.40,
        'font': 0.35,
    }

    overall_score = (
        metadata_score * weights['metadata'] +
        ela_score * weights['ela'] +
        font_score * weights['font']
    )

    # Determine result and generate explanation
    explanations = []

    if metadata_score >= 0.9:
        explanations.append("Metadata appears clean with no suspicious editing software detected.")
    elif metadata_score >= 0.7:
        explanations.append("Metadata shows minor modifications but within acceptable range.")
    else:
        explanations.append("Metadata indicates potential editing with suspicious software or significant modifications.")

    if ela_score >= 0.9:
        explanations.append("Error Level Analysis shows consistent compression throughout the document.")
    elif ela_score >= 0.7:
        explanations.append("ELA shows some variation in compression levels, minor inconsistencies detected.")
    else:
        explanations.append("ELA reveals significant compression inconsistencies suggesting potential image manipulation.")

    if font_score >= 0.9:
        explanations.append("Font usage is consistent with a legitimate document.")
    elif font_score >= 0.7:
        explanations.append("Multiple fonts detected but within reasonable limits.")
    else:
        explanations.append("Excessive font variation detected, possibly indicating content from multiple sources.")

    if overall_score >= 0.8:
        result = "PASS"
        assessment = "Document appears authentic. " + " ".join(explanations)
    elif overall_score >= 0.6:
        result = "FLAG"
        assessment = "Some indicators require human review. " + " ".join(explanations)
    else:
        result = "FAIL"
        assessment = "Potential forgery detected - manual verification required. " + " ".join(explanations)

    flags = []
    if metadata_score < 0.7:
        flags.append("SUSPICIOUS_METADATA")
    if ela_score < 0.7:
        flags.append("ELA_ANOMALY")
    if font_score < 0.7:
        flags.append("FONT_INCONSISTENCY")
    if result in ["FLAG", "FAIL"]:
        flags.append("FORGERY_FLAG")

    return {
        "overall_score": float(overall_score),
        "result": result,
        "assessment": assessment,
        "flags": flags,
        "layer_scores": {
            "metadata": float(metadata_score),
            "ela": float(ela_score),
            "font": float(font_score),
        },
        "layer_explanations": {
            "metadata": explanations[0],
            "ela": explanations[1],
            "font": explanations[2],
        },
        "weights": weights,
    }
