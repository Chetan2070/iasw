
"""
Tools for OCR Agent

Provides tools for extracting text from documents.
"""

import os
import logging
from typing import Tuple, List
from PIL import Image

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def preprocess_image(image: Image.Image) -> Image.Image:
    """Apply preprocessing to improve OCR quality."""
    if image.mode != 'L':
        image = image.convert('L')

    min_dimension = 1000
    if min(image.size) < min_dimension:
        ratio = min_dimension / min(image.size)
        new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    return image


def _extract_text_from_image(image_path: str) -> Tuple[str, float, List[dict]]:
    """Extract text from an image using Tesseract OCR."""
    import pytesseract

    image = Image.open(image_path)
    image = preprocess_image(image)

    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    words = []
    confidences = []
    word_data = []

    for i, word in enumerate(data['text']):
        if word.strip():
            conf = int(data['conf'][i])
            if conf > 0:
                words.append(word)
                confidences.append(conf)
                word_data.append({
                    'word': word,
                    'confidence': conf / 100.0,
                })

    text = ' '.join(words)
    avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0

    return text, avg_confidence, word_data


def _extract_text_from_pdf(pdf_path: str) -> Tuple[str, float, List[dict], int]:
    """Extract text from a PDF document."""
    import fitz

    doc = fitz.open(pdf_path)
    all_text = []
    all_confidences = []
    all_word_data = []
    pages_processed = 0

    for page_num, page in enumerate(doc):
        pages_processed += 1
        text = page.get_text()

        if text.strip():
            all_text.append(text)
            all_confidences.append(0.95)
            all_word_data.extend([
                {'word': w, 'confidence': 0.95, 'page': page_num}
                for w in text.split() if w.strip()
            ])
        else:
            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")

            temp_path = f"/tmp/page_{page_num}.png"
            with open(temp_path, 'wb') as f:
                f.write(img_data)

            text, conf, word_data = _extract_text_from_image(temp_path)
            all_text.append(text)
            all_confidences.append(conf)
            all_word_data.extend(word_data)

            os.remove(temp_path)

    doc.close()

    combined_text = '\n\n'.join(all_text)
    avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

    return combined_text, avg_confidence, all_word_data, pages_processed


@tool
def extract_text_from_document(document_path: str) -> dict:
    """
    Extract text from a document using OCR.

    Args:
        document_path: Path to the document file (PDF or image)

    Returns:
        Dict with extracted text, confidence score, and metadata
    """
    try:
        ext = os.path.splitext(document_path)[1].lower()

        if ext == '.pdf':
            text, confidence, word_data, pages = _extract_text_from_pdf(document_path)
            method = "tesseract_pdf"
        elif ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif']:
            text, confidence, word_data = _extract_text_from_image(document_path)
            pages = 1
            method = "tesseract_image"
        else:
            return {
                "success": False,
                "error": f"Unsupported file type: {ext}",
                "text": "",
                "confidence": 0.0,
            }

        return {
            "success": True,
            "text": text,
            "confidence": float(confidence),
            "method": method,
            "pages_processed": pages,
            "word_count": len(word_data),
        }

    except Exception as e:
        logger.error(f"OCR extraction error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "text": "",
            "confidence": 0.0,
        }


@tool
def check_ocr_quality(confidence: float) -> dict:
    """
    Assess the quality of OCR output based on confidence score.

    Args:
        confidence: OCR confidence score (0.0-1.0)

    Returns:
        Quality assessment with flags and recommendations
    """
    flags = []
    recommendation = "proceed"

    if confidence < 0.5:
        flags.append("OCR_VERY_LOW_QUALITY")
        recommendation = "retry_with_fallback"
    elif confidence < 0.6:
        flags.append("OCR_LOW_QUALITY")
        recommendation = "consider_fallback"
    elif confidence < 0.8:
        flags.append("OCR_MEDIUM_CONF")
        recommendation = "proceed_with_caution"

    return {
        "quality": "good" if confidence >= 0.8 else "medium" if confidence >= 0.6 else "low",
        "flags": flags,
        "recommendation": recommendation,
        "needs_fallback": confidence < 0.5,
    }
