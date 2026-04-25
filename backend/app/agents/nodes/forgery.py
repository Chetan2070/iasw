"""
Forgery Detection Node

Detects potential document tampering using multiple analysis layers.
"""

import os
import logging
import hashlib
from typing import Dict, Any, Tuple
from PIL import Image
import io

from app.agents.state import ProcessingState
from app.config import settings

logger = logging.getLogger(__name__)


def analyze_metadata(file_path: str) -> Tuple[float, dict]:
    """
    Analyze document metadata for suspicious patterns.

    Checks:
        - Creation vs modification dates
        - Software/producer information
        - Suspicious metadata patterns

    Returns:
        - score: 0.0 (suspicious) to 1.0 (clean)
        - details: Analysis details
    """
    details = {}
    score = 1.0  # Start with perfect score

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

            # Check for suspicious producers
            suspicious_producers = ['photoshop', 'canva', 'gimp', 'paint']
            producer_lower = details['producer'].lower()
            if any(sp in producer_lower for sp in suspicious_producers):
                score -= 0.3
                details['warning'] = 'Suspicious producer software detected'

            # Check if modification date is much later than creation
            # (simplified check - in production would parse dates properly)
            if details['mod_date'] and details['creation_date']:
                if details['mod_date'] != details['creation_date']:
                    score -= 0.1
                    details['note'] = 'Document was modified after creation'

            doc.close()

        elif ext in ['.jpg', '.jpeg', '.png']:
            from PIL import Image
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

    return max(0.0, score), details


def analyze_ela(file_path: str) -> Tuple[float, dict]:
    """
    Error Level Analysis - detects edited regions.

    ELA works by re-saving the image and comparing compression artifacts.
    Edited regions show different error levels than original content.

    Returns:
        - score: 0.0 (likely edited) to 1.0 (consistent)
        - details: Analysis details
    """
    details = {}

    try:
        from PIL import Image
        import numpy as np

        # Load image
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

        # Save at known quality and compare
        temp_path = '/tmp/ela_temp.jpg'
        img.save(temp_path, 'JPEG', quality=90)

        # Load resaved image
        resaved = Image.open(temp_path)

        # Calculate difference
        original_array = np.array(img, dtype=np.float32)
        resaved_array = np.array(resaved, dtype=np.float32)

        diff = np.abs(original_array - resaved_array)
        avg_diff = np.mean(diff)
        max_diff = np.max(diff)

        # Calculate score based on difference distribution
        # Higher variance in differences suggests tampering
        std_diff = np.std(diff)

        # Normalize to 0-1 score (lower diff variance = higher score)
        score = 1.0 - min(std_diff / 50.0, 1.0)

        details['avg_difference'] = float(avg_diff)
        details['max_difference'] = float(max_diff)
        details['std_difference'] = float(std_diff)

        # Cleanup
        os.remove(temp_path)
        resaved.close()
        img.close()

    except Exception as e:
        logger.warning(f"ELA analysis error: {e}")
        details['error'] = str(e)
        score = 0.7  # Neutral score on error

    return max(0.0, min(1.0, score)), details


def analyze_font_consistency(file_path: str) -> Tuple[float, dict]:
    """
    Analyze font consistency in the document.

    Checks for multiple fonts in areas that should have consistent typography.

    Returns:
        - score: 0.0 (inconsistent) to 1.0 (consistent)
        - details: Analysis details
    """
    details = {}
    score = 0.85  # Default to slightly below perfect

    try:
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.pdf':
            import fitz
            doc = fitz.open(file_path)

            fonts_used = set()
            for page in doc:
                font_list = page.get_fonts()
                for font in font_list:
                    fonts_used.add(font[3])  # Font name

            details['fonts_found'] = list(fonts_used)
            details['font_count'] = len(fonts_used)

            # Many different fonts might indicate tampering
            if len(fonts_used) > 5:
                score -= 0.2
                details['warning'] = 'Multiple fonts detected'
            elif len(fonts_used) <= 2:
                score = 0.95  # Consistent fonts

            doc.close()

        else:
            # For images, we can't easily analyze fonts
            details['note'] = 'Font analysis limited for images'
            score = 0.8

    except Exception as e:
        logger.warning(f"Font analysis error: {e}")
        details['error'] = str(e)

    return max(0.0, min(1.0, score)), details


def analyze_ml_model(file_path: str) -> Tuple[float, dict]:
    """
    ML-based forgery detection (simulated).

    In production, this would use a trained model for forgery detection.
    For the prototype, we simulate based on heuristics.

    Returns:
        - score: 0.0 (likely forged) to 1.0 (likely authentic)
        - details: Analysis details
    """
    details = {}

    try:
        # Calculate file hash for uniqueness check
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()

        details['file_hash'] = file_hash

        # Get file size
        file_size = os.path.getsize(file_path)
        details['file_size'] = file_size

        # Simulate ML prediction based on file characteristics
        # In production: load and run actual trained model

        # Base score
        score = 0.85

        # Very small files might be suspicious
        if file_size < 50000:  # Less than 50KB
            score -= 0.1
            details['warning'] = 'Unusually small file size'

        # Very large files are usually authentic scans
        if file_size > 2000000:  # More than 2MB
            score += 0.05

        details['model'] = 'simulated_v1'
        details['prediction'] = 'likely_authentic' if score > 0.7 else 'needs_review'

    except Exception as e:
        logger.warning(f"ML analysis error: {e}")
        details['error'] = str(e)
        score = 0.7

    return max(0.0, min(1.0, score)), details


async def forgery_node(state: ProcessingState) -> Dict[str, Any]:
    """
    Detects potential document forgery using multiple layers.

    Detection Layers:
        1. Metadata Analysis (20%) - PDF creation/mod dates, software
        2. ELA Analysis (30%) - Error Level Analysis for edits
        3. Font Consistency (20%) - Font mismatches in text
        4. ML Model (30%) - Pattern-based detection

    Input State:
        - document_path

    Output State Updates:
        - forgery_score: float (0.0 = forged, 1.0 = authentic)
        - forgery_result: str (PASS/FLAG/FAIL)
        - forgery_details: dict with per-layer scores
        - flags: adds FORGERY_FLAG if result is FLAG/FAIL
        - current_step: "forgery"
    """
    request_id = state.get('request_id', 'unknown')
    document_path = state.get('document_path', '')

    logger.info(f"[{request_id}] Running forgery detection")

    try:
        # Run all detection layers
        metadata_score, metadata_details = analyze_metadata(document_path)
        ela_score, ela_details = analyze_ela(document_path)
        font_score, font_details = analyze_font_consistency(document_path)
        ml_score, ml_details = analyze_ml_model(document_path)

        # Calculate weighted score
        weights = {
            'metadata': 0.20,
            'ela': 0.30,
            'font': 0.20,
            'ml': 0.30,
        }

        forgery_score = (
            metadata_score * weights['metadata'] +
            ela_score * weights['ela'] +
            font_score * weights['font'] +
            ml_score * weights['ml']
        )

        # Determine result
        if forgery_score > settings.FORGERY_PASS_THRESHOLD:
            forgery_result = "PASS"
        elif forgery_score >= settings.FORGERY_FAIL_THRESHOLD:
            forgery_result = "FLAG"
        else:
            forgery_result = "FAIL"

        # Build details - ensure all values are JSON serializable
        forgery_details = {
            'metadata': {'score': float(metadata_score), 'details': metadata_details},
            'ela': {'score': float(ela_score), 'details': ela_details},
            'font': {'score': float(font_score), 'details': font_details},
            'ml': {'score': float(ml_score), 'details': ml_details},
            'weights': weights,
        }

        # Update flags
        flags = list(state.get('flags', []))
        if forgery_result in ["FLAG", "FAIL"]:
            flags.append("FORGERY_FLAG")
            if forgery_result == "FAIL":
                logger.warning(f"[{request_id}] Potential forgery detected: score={forgery_score:.2f}")

        logger.info(f"[{request_id}] Forgery detection: {forgery_result} (score: {forgery_score:.2f})")

        return {
            "forgery_score": float(forgery_score),
            "forgery_result": forgery_result,
            "forgery_details": forgery_details,
            "flags": flags,
            "current_step": "forgery",
        }

    except Exception as e:
        logger.error(f"[{request_id}] Forgery detection failed: {str(e)}")

        return {
            "forgery_score": 0.7,  # Neutral score on error
            "forgery_result": "FLAG",
            "forgery_details": {"error": str(e)},
            "flags": state.get('flags', []) + ["FORGERY_CHECK_ERROR"],
            "errors": state.get('errors', []) + [f"Forgery detection failed: {str(e)}"],
            "current_step": "forgery",
        }
