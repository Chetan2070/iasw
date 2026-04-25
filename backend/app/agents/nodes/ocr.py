"""
OCR Node

Performs OCR on the uploaded document to extract text.
"""

import os
import logging
from typing import Dict, Any, List, Tuple
from PIL import Image
import io

from app.agents.state import ProcessingState
from app.config import settings

logger = logging.getLogger(__name__)


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Apply preprocessing to improve OCR quality.

    Steps:
        1. Convert to grayscale
        2. Resize if too small
        3. Increase contrast
    """
    # Convert to grayscale
    if image.mode != 'L':
        image = image.convert('L')

    # Resize if too small (min 300 DPI equivalent)
    min_dimension = 1000
    if min(image.size) < min_dimension:
        ratio = min_dimension / min(image.size)
        new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    return image


def extract_text_from_image(image_path: str) -> Tuple[str, float, List[dict]]:
    """
    Extract text from an image using Tesseract OCR.

    Returns:
        - text: Extracted text
        - confidence: Average confidence score
        - word_confidences: Per-word confidence data
    """
    try:
        import pytesseract

        # Load and preprocess image
        image = Image.open(image_path)
        image = preprocess_image(image)

        # Run OCR with detailed output
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        # Extract text and calculate confidence
        words = []
        confidences = []
        word_data = []

        for i, word in enumerate(data['text']):
            if word.strip():
                conf = int(data['conf'][i])
                if conf > 0:  # Ignore low confidence items
                    words.append(word)
                    confidences.append(conf)
                    word_data.append({
                        'word': word,
                        'confidence': conf / 100.0,
                        'left': data['left'][i],
                        'top': data['top'][i],
                        'width': data['width'][i],
                        'height': data['height'][i],
                    })

        text = ' '.join(words)
        avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0

        return text, avg_confidence, word_data

    except Exception as e:
        logger.exception("OCR error")
        raise


def extract_text_from_pdf(pdf_path: str) -> Tuple[str, float, List[dict], int]:
    """
    Extract text from a PDF document.

    First tries to extract embedded text, falls back to OCR if needed.

    Returns:
        - text: Extracted text
        - confidence: Average confidence score
        - word_confidences: Per-word confidence data
        - pages_processed: Number of pages
    """
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        all_text = []
        all_confidences = []
        all_word_data = []
        pages_processed = 0

        for page_num, page in enumerate(doc):
            pages_processed += 1

            # Try to extract embedded text first
            text = page.get_text()

            if text.strip():
                # PDF has embedded text - high confidence
                all_text.append(text)
                all_confidences.append(0.95)  # Embedded text is reliable
                all_word_data.extend([
                    {'word': w, 'confidence': 0.95, 'page': page_num}
                    for w in text.split() if w.strip()
                ])
            else:
                # Need to OCR this page
                pix = page.get_pixmap(dpi=300)
                img_data = pix.tobytes("png")

                # Save temporarily and OCR
                temp_path = f"/tmp/page_{page_num}.png"
                with open(temp_path, 'wb') as f:
                    f.write(img_data)

                text, conf, word_data = extract_text_from_image(temp_path)
                all_text.append(text)
                all_confidences.append(conf)
                all_word_data.extend(word_data)

                # Cleanup
                os.remove(temp_path)

        doc.close()

        combined_text = '\n\n'.join(all_text)
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

        return combined_text, avg_confidence, all_word_data, pages_processed

    except Exception as e:
        logger.exception("PDF extraction error")
        raise


async def ocr_node(state: ProcessingState) -> Dict[str, Any]:
    """
    Performs OCR on the uploaded document.

    Process:
        1. Detect file type (PDF or image)
        2. Extract text using appropriate method
        3. Calculate confidence scores

    Input State:
        - document_path

    Output State Updates:
        - ocr_text: str
        - ocr_confidence: float
        - ocr_word_confidences: List[dict]
        - ocr_method: str
        - ocr_pages_processed: int
        - current_step: "ocr"
        - flags: may add OCR_LOW_QUALITY flag
    """
    request_id = state.get('request_id', 'unknown')
    document_path = state.get('document_path', '')

    logger.info(f"[{request_id}] Starting OCR on {document_path}")

    try:
        # Determine file type
        ext = os.path.splitext(document_path)[1].lower()

        if ext == '.pdf':
            text, confidence, word_data, pages = extract_text_from_pdf(document_path)
            method = "tesseract_pdf"
        elif ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif']:
            text, confidence, word_data = extract_text_from_image(document_path)
            pages = 1
            method = "tesseract_image"
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        # Check for low quality OCR
        flags = list(state.get('flags', []))
        if confidence < 0.6:
            flags.append("OCR_LOW_QUALITY")
            logger.warning(f"[{request_id}] Low OCR confidence: {confidence:.2f}")
        elif confidence < 0.9:
            flags.append("OCR_MEDIUM_CONF")

        logger.info(f"[{request_id}] OCR complete - {len(text)} chars, confidence: {confidence:.2f}")

        return {
            "ocr_text": text,
            "ocr_confidence": float(confidence),
            "ocr_word_confidences": word_data,
            "ocr_method": method,
            "ocr_pages_processed": pages,
            "flags": flags,
            "current_step": "ocr",
        }

    except Exception as e:
        logger.exception(f"[{request_id}] OCR failed")
        return {
            "ocr_text": "",
            "ocr_confidence": 0.0,
            "ocr_word_confidences": [],
            "ocr_method": "failed",
            "ocr_pages_processed": 0,
            "errors": state.get('errors', []) + [f"OCR failed: {str(e)}"],
            "current_step": "ocr",
        }


def route_after_ocr(state: ProcessingState) -> str:
    """
    Route after OCR node.

    Returns:
        - "fallback" if confidence is too low
        - "continue" otherwise
    """
    confidence = state.get('ocr_confidence', 0.0)

    # If confidence is very low, try fallback OCR
    if confidence < settings.OCR_CONFIDENCE_THRESHOLD and state.get('ocr_method') != 'google_vision':
        return "fallback"

    return "continue"


async def fallback_ocr_node(state: ProcessingState) -> Dict[str, Any]:
    """
    Fallback OCR using Google Cloud Vision (simulated).

    In production, this would call Google Cloud Vision API.
    For the prototype, we'll simulate improved OCR.
    """
    request_id = state.get('request_id', 'unknown')
    logger.info(f"[{request_id}] Running fallback OCR (simulated)")

    # In production: call Google Cloud Vision API
    # For prototype: simulate slightly better results

    current_text = state.get('ocr_text', '')
    current_confidence = state.get('ocr_confidence', 0.0)

    # Simulate improvement
    improved_confidence = min(current_confidence + 0.15, 0.85)

    flags = list(state.get('flags', []))
    flags.append("FALLBACK_OCR_USED")

    return {
        "ocr_confidence": float(improved_confidence),
        "ocr_method": "google_vision_simulated",
        "flags": flags,
        "current_step": "fallback_ocr",
    }
