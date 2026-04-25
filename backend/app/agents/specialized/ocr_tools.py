"""
Tools for OCR Agent

Provides tools for text extraction from documents using OCR.
"""

import os
import logging
from typing import Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def extract_text_from_document(file_path: str) -> dict:
    """
    Extract text from a document using OCR.

    Supports PDF, JPEG, PNG, and TIFF files.
    Uses Tesseract OCR for text extraction.

    Args:
        file_path: Path to the document file

    Returns:
        Dictionary with extracted text and confidence score
    """
    import pytesseract
    from PIL import Image

    try:
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.pdf':
            import fitz
            doc = fitz.open(file_path)
            all_text = []
            all_confidences = []

            for page_num, page in enumerate(doc):
                pix = page.get_pixmap(dpi=150)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                text = pytesseract.image_to_string(img)
                all_text.append(text)

                data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                confidences = [int(c) for c in data['conf'] if c != '-1' and int(c) > 0]
                if confidences:
                    all_confidences.extend(confidences)

            doc.close()
            extracted_text = "\n\n--- PAGE BREAK ---\n\n".join(all_text)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

        else:
            img = Image.open(file_path)
            extracted_text = pytesseract.image_to_string(img)

            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            confidences = [int(c) for c in data['conf'] if c != '-1' and int(c) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            img.close()

        return {
            "text": extracted_text,
            "confidence": avg_confidence / 100.0,
            "char_count": len(extracted_text),
            "word_count": len(extracted_text.split()),
        }

    except Exception as e:
        logger.exception("OCR extraction error")
        return {
            "text": "",
            "confidence": 0.0,
            "char_count": 0,
            "word_count": 0,
            "error": str(e),
        }


@tool
def check_ocr_quality(text: str, confidence: float) -> dict:
    """
    Assess the quality of OCR output.

    Checks for common OCR quality issues:
    - Low confidence scores
    - Too little text extracted
    - High ratio of special characters (garbled text)

    Args:
        text: The extracted OCR text
        confidence: The OCR confidence score (0-1)

    Returns:
        Quality assessment with flags and recommendations
    """
    issues = []
    quality_score = 1.0

    # Check confidence
    if confidence < 0.6:
        issues.append("LOW_OCR_CONFIDENCE")
        quality_score -= 0.3
    elif confidence < 0.8:
        issues.append("MEDIUM_OCR_CONFIDENCE")
        quality_score -= 0.1

    # Check text length
    if len(text) < 100:
        issues.append("INSUFFICIENT_TEXT")
        quality_score -= 0.2

    # Check for garbled text (high special character ratio)
    if text:
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        special_ratio = special_chars / len(text)
        if special_ratio > 0.3:
            issues.append("POSSIBLE_GARBLED_TEXT")
            quality_score -= 0.2

    # Determine overall quality
    if quality_score >= 0.8:
        quality = "GOOD"
        recommendation = "Proceed with extraction"
    elif quality_score >= 0.5:
        quality = "ACCEPTABLE"
        recommendation = "Proceed with caution, flag for review"
    else:
        quality = "POOR"
        recommendation = "Consider alternative OCR method or manual review"

    return {
        "quality": quality,
        "quality_score": max(0.0, quality_score),
        "issues": issues,
        "recommendation": recommendation,
        "text_length": len(text),
        "confidence": confidence,
    }
