"""
Forgery Detection Node

Detects potential document tampering using multiple analysis layers.
"""


import os
import uuid
import logging
import hashlib
import asyncio
import tempfile
from typing import Dict, Any, Tuple
from datetime import datetime, timezone
from PIL import Image

from app.agents.state import ProcessingState
from app.config import settings

logger = logging.getLogger(__name__)


FONT_THRESHOLDS: Dict[str, int] = {
    "Gazette Notification,":          3,
    "MARRIAGE CERTIFICATE": 4,
    "BANK_STATEMENT":       3,
    "ID_CARD":              2,
    "INVOICE":              4,
}
DEFAULT_FONT_THRESHOLD = 5


# ─────────────────────────────────────────────
# ELA baseline std_diff per document type
# Used to normalize ELA scores contextually
# ─────────────────────────────────────────────
ELA_BASELINES: Dict[str, float] = {
    "Gazette Notification,": 12.0,
    "MARRIAGE_CERTIFICATE": 15.0,
    "BANK_STATEMENT":       10.0,
    "ID_CARD":              8.0,
    "Deed Poll":              10.0,
}
DEFAULT_ELA_BASELINE = 20.0


# ─────────────────────────────────────────────
# Suspicious software signatures
# Loaded from config in production
# ─────────────────────────────────────────────
SUSPICIOUS_SOFTWARE = [
    "photoshop", "gimp", "paint", "canva",
    "illustrator", "inkscape", "affinity",
    "pixlr", "fotor", "polarr",
]

SUSPICIOUS_PDF_PRODUCERS = [
    "photoshop", "canva", "gimp", "paint",
    "smallpdf", "pdf24", "ilovepdf", "sejda",
]


# ══════════════════════════════════════════════
# LAYER 1 — Metadata Analysis
# ══════════════════════════════════════════════

def analyze_metadata(file_path: str) -> Tuple[float, dict]:
    """
    Analyze document metadata for suspicious patterns.
    This function is the first line of forensic defense. It never looks at what the document says — it looks at what the document reveals about itself through hidden technical data that most users don't even know exists.
    Every file carries invisible metadata baked in by the software that created it. This function reads that hidden layer and asks: "Does this metadata tell the story of a genuine document, or does it contradict that story?"
    """
    details = {}
    score = 1.0

    try:
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            import fitz
            doc = fitz.open(file_path)
            metadata = doc.metadata

            details["producer"] = metadata.get("producer", "")
            details["creator"] = metadata.get("creator", "")
            details["creation_date"] = metadata.get("creationDate", "")
            details["mod_date"] = metadata.get("modDate", "")

            # Check producer against suspicious software list
            producer_lower = details["producer"].lower()
            for sig in SUSPICIOUS_PDF_PRODUCERS:
                if sig in producer_lower:
                    score -= 0.3
                    details["warning"] = f"Suspicious producer software: {details['producer']}"
                    break

            # Proper date comparison — PDF dates look like "D:20240315102233"
            creation = details["creation_date"]
            mod = details["mod_date"]
            if creation and mod and len(creation) >= 8 and len(mod) >= 8:
                # Strip "D:" prefix and compare date portions
                creation_clean = creation.lstrip("D:").strip()[:8]
                mod_clean = mod.lstrip("D:").strip()[:8]
                if mod_clean > creation_clean:
                    score -= 0.1
                    details["note"] = "Document was modified after creation"

            doc.close()

        elif ext in [".jpg", ".jpeg", ".png", ".tiff", ".tif"]:
            with Image.open(file_path) as img:
                # FIX: use public API getexif() not private _getexif()
                exif_data = img.getexif()

                if exif_data:
                    from PIL.ExifTags import TAGS
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)
                        if tag in ["Software", "ProcessingSoftware"]:
                            value_str = str(value)
                            details[tag] = value_str
                            for sig in SUSPICIOUS_SOFTWARE:
                                if sig in value_str.lower():
                                    score -= 0.25
                                    details["warning"] = f"Editing software in EXIF: {value_str}"
                                    break
                else:
                    # No EXIF at all — could mean it was stripped (suspicious)
                    details["note"] = "No EXIF data found — may have been stripped"
                    score -= 0.05

    except Exception as e:
        logger.warning(f"Metadata analysis error: {e}")
        details["error"] = str(e)

    return max(0.0, score), details


def _run_ela_on_image(img: Image.Image, document_type: str, request_id: str) -> Tuple[float, dict]:
    """
    Run ELA on a single PIL Image object.

    """
    import numpy as np

    details: dict = {}

    # FIX: use a unique temp path per request to prevent race conditions
    unique_suffix = f"ela_{request_id}_{uuid.uuid4().hex}.jpg"

    with tempfile.NamedTemporaryFile(suffix=unique_suffix, delete=True) as tmp:
        img_rgb = img.convert("RGB")
        img_rgb.save(tmp.name, "JPEG", quality=90)

        resaved = Image.open(tmp.name).convert("RGB")

        original_arr = np.array(img_rgb, dtype=np.float32)
        resaved_arr = np.array(resaved, dtype=np.float32)

        diff = np.abs(original_arr - resaved_arr)
        avg_diff = float(np.mean(diff))
        max_diff = float(np.max(diff))
        std_diff = float(np.std(diff))

        resaved.close()

    details["avg_difference"] = avg_diff
    details["max_difference"] = max_diff
    details["std_difference"] = std_diff

    # FIX: use per-document-type baseline instead of hardcoded 50.0
    baseline = ELA_BASELINES.get(document_type, DEFAULT_ELA_BASELINE)
    score = 1.0 - min(std_diff / (baseline * 3), 1.0)

    return max(0.0, min(1.0, score)), details


def analyze_ela(
        file_path: str,
        document_type: str = "UNKNOWN",
        request_id: str = "unknown",
) -> Tuple[float, dict]:
    """
    Error Level Analysis across all pages.
    """
    details: dict = {}
    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == ".pdf":
            import fitz
            doc = fitz.open(file_path)
            page_scores = []
            page_details = []

            for page_num, page in enumerate(doc):
                # FIX: analyze every page, not just doc[0]
                pix = page.get_pixmap(dpi=150)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                s, d = _run_ela_on_image(img, document_type, f"{request_id}_p{page_num}")
                page_scores.append(s)
                page_details.append({f"page_{page_num}": d})
                img.close()

            doc.close()

            # FIX: use MINIMUM score — most suspicious page determines result
            score = min(page_scores) if page_scores else 0.7
            details["pages_analyzed"] = len(page_scores)
            details["page_scores"] = page_scores
            details["worst_page"] = page_scores.index(score)
            details.update({k: v for d in page_details for k, v in d.items()})

        elif ext in [".jpg", ".jpeg", ".tiff", ".tif", ".bmp"]:
            with Image.open(file_path) as img:
                score, details = _run_ela_on_image(img, document_type, request_id)

        elif ext == ".png":
            # FIX: ELA is meaningless on PNG (lossless — no compression history)
            details["note"] = "ELA skipped: PNG is lossless, ELA unreliable"
            details["recommendation"] = "Use pixel noise analysis instead for PNG"
            score = 0.75  # neutral, don't penalize or reward
        else:
            details["note"] = f"ELA not supported for {ext}"
            score = 0.75

    except Exception as e:
        logger.warning(f"ELA analysis error: {e}")
        details["error"] = str(e)
        score = 0.5  # FIX: errors are suspicious, not neutral

    return max(0.0, min(1.0, score)), details


# ══════════════════════════════════════════════
# LAYER 3 — Font Consistency
# ══════════════════════════════════════════════

def analyze_font_consistency(
        file_path: str,
        document_type: str = "UNKNOWN",
) -> Tuple[float, dict]:
    """
    Analyze font consistency in the document.

    """
    details: dict = {}
    score = 0.85
    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == ".pdf":
            import fitz
            doc = fitz.open(file_path)

            fonts_used: set = set()
            base_fonts: set = set()

            for page in doc:
                for font in page.get_fonts():
                    font_name = font[3]  # full name e.g. "Arial-Bold"
                    fonts_used.add(font_name)
                    # Extract base family (everything before first hyphen/space)
                    base = font_name.split("-")[0].split(" ")[0]
                    base_fonts.add(base)

            doc.close()

            details["fonts_found"] = sorted(fonts_used)
            details["base_font_families"] = sorted(base_fonts)
            details["font_count"] = len(fonts_used)
            details["base_family_count"] = len(base_fonts)

            # FIX: threshold per document type
            threshold = FONT_THRESHOLDS.get(document_type, DEFAULT_FONT_THRESHOLD)
            details["threshold_used"] = threshold

            # Judge by base families, not variants
            if len(base_fonts) > threshold:
                score -= 0.25
                details["warning"] = f"Too many font families ({len(base_fonts)} > {threshold})"
            elif len(base_fonts) == 1:
                score = 0.98  # single font family = very consistent
            elif len(base_fonts) <= 2:
                score = 0.92  # two families = normal (body + heading)

        else:
            details["note"] = "Font analysis only available for PDFs"
            score = 0.80  # neutral for images

    except Exception as e:
        logger.warning(f"Font analysis error: {e}")
        details["error"] = str(e)

    return max(0.0, min(1.0, score)), details


# ══════════════════════════════════════════════
# LAYER 4 — Real ML Model (EfficientNet)
# ══════════════════════════════════════════════

def _load_ml_model():
    """
    Load EfficientNet model for forgery detection.

    Uses timm (PyTorch Image Models) — a library of pre-trained vision models.
    The model is fine-tuned for document forgery detection.

    In production: load your own fine-tuned checkpoint.
    Here: uses EfficientNet-B0 pretrained on ImageNet as a feature extractor,
    combined with heuristic scoring on top.

    To properly fine-tune for forgery detection, you would:
        1. Collect dataset of real vs forged documents
        2. Fine-tune EfficientNet on that dataset
        3. Save checkpoint and load it here
    """
    try:
        import torch
        import timm

        # Load EfficientNet-B0 — lightweight, fast, good accuracy
        model = timm.create_model(
            "efficientnet_b0",
            pretrained=True,
            num_classes=2,       # binary: authentic (1) vs forged (0)
            in_chans=3,
        )
        model.eval()

        # In production, load your fine-tuned weights:
        # checkpoint_path = settings.FORGERY_MODEL_CHECKPOINT
        # if os.path.exists(checkpoint_path):
        #     model.load_state_dict(torch.load(checkpoint_path, map_location="cpu"))
        #     logger.info("Loaded fine-tuned forgery detection model")
        # else:
        #     logger.warning("No fine-tuned checkpoint found — using pretrained weights")

        return model

    except ImportError:
        logger.warning("timm/torch not installed — ML model unavailable")
        return None


# Module-level model singleton (loaded once, reused across requests)
_ml_model = None

def _get_ml_model():
    global _ml_model
    if _ml_model is None:
        _ml_model = _load_ml_model()
    return _ml_model


def _preprocess_for_efficientnet(img: Image.Image):
    """Preprocess image to EfficientNet input format."""
    import torch
    import torchvision.transforms as T

    transform = T.Compose([
        T.Resize((224, 224)),
        T.ToTensor(),
        T.Normalize(
            mean=[0.485, 0.456, 0.406],   # ImageNet mean
            std=[0.229, 0.224, 0.225],    # ImageNet std
        ),
    ])
    tensor = transform(img.convert("RGB"))
    return tensor.unsqueeze(0)  # add batch dimension → [1, 3, 224, 224]


def analyze_ml_model(
        file_path: str,
        document_type: str = "UNKNOWN",
) -> Tuple[float, dict]:
    """
    ML-based forgery detection using EfficientNet-B0.

    The model outputs a probability for two classes:
        Class 0: Forged
        Class 1: Authentic

    Score = probability of class 1 (authentic).

    Falls back to heuristic scoring if model unavailable.
    """
    details: dict = {}
    file_size = os.path.getsize(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    # Always compute file hash for audit trail
    with open(file_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()  # FIX: sha256 not md5
    details["file_hash"] = file_hash
    details["file_size"] = file_size

    model = _get_ml_model()

    if model is not None:
        try:
            import torch
            import torch.nn.functional as F

            # Load document as image
            if ext == ".pdf":
                import fitz
                doc = fitz.open(file_path)
                # Analyze first page for ML (representative)
                pix = doc[0].get_pixmap(dpi=150)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                doc.close()
            else:
                img = Image.open(file_path).convert("RGB")

            # Run inference
            tensor = _preprocess_for_efficientnet(img)

            with torch.no_grad():
                logits = model(tensor)                        # [1, 2]
                probs = F.softmax(logits, dim=1)              # [1, 2]
                authentic_prob = probs[0, 1].item()           # class 1 = authentic
                forged_prob = probs[0, 0].item()              # class 0 = forged

            score = authentic_prob

            details["model"] = "efficientnet_b0"
            details["authentic_probability"] = round(authentic_prob, 4)
            details["forged_probability"] = round(forged_prob, 4)
            details["prediction"] = "likely_authentic" if score > 0.6 else "needs_review"
            details["model_source"] = "pretrained_imagenet"
            details["note"] = (
                "Model uses ImageNet pretrained weights. "
                "Fine-tune on document forgery dataset for production accuracy."
            )

            img.close() if hasattr(img, "close") else None

        except Exception as e:
            logger.warning(f"ML model inference failed: {e}")
            details["ml_error"] = str(e)
            # Fall through to heuristic fallback below
            model = None

    if model is None:
        # Heuristic fallback when model unavailable
        score = 0.75  # conservative base

        if file_size < 10_000:
            score -= 0.20
            details["warning"] = "File suspiciously small (< 10KB)"
        elif file_size < 50_000:
            score -= 0.10
            details["note"] = "Small file size"
        elif file_size > 2_000_000:
            score = min(score + 0.05, 0.90)
            details["note"] = "Large file — likely authentic scan"

        details["model"] = "heuristic_fallback"
        details["prediction"] = "likely_authentic" if score > 0.6 else "needs_review"

    return max(0.0, min(1.0, score)), details


# ══════════════════════════════════════════════
# MAIN NODE
# ══════════════════════════════════════════════

async def forgery_node(state: ProcessingState) -> Dict[str, Any]:
    """
    Detects potential document forgery using multiple layers.

    Detection Layers:
        1. Metadata Analysis (20%) — PDF/EXIF software signatures, date anomalies
        2. ELA Analysis (30%)      — Compression artifact inconsistencies
        3. Font Consistency (20%)  — Font family count vs document-type threshold
        4. ML Model (30%)          — EfficientNet-B0 image classifier

    Input State:
        - document_path
        - detected_document_type (from classifier)
        - file_metadata (optional, from parallel metadata_node)
        - metadata_flags (optional, from parallel metadata_node)

    Output State Updates:
        - forgery_score: float (0.0 = forged, 1.0 = authentic)
        - forgery_result: str (PASS / FLAG / FAIL)
        - forgery_details: dict with per-layer scores and details
        - flags: adds FORGERY_FLAG if result is FLAG or FAIL
        - current_step: "forgery"
    """
    request_id = state.get("request_id", "unknown")
    document_path = state.get("document_path", "")
    document_type = state.get("detected_document_type") or state.get("document_type", "UNKNOWN")

    logger.info(f"[{request_id}] Running forgery detection on {document_type}")

    try:
        # ── Metadata: reuse pre-extracted results if available ──────────────
        pre_extracted_metadata = state.get("file_metadata", {})
        pre_extracted_flags = state.get("metadata_flags", [])

        if pre_extracted_metadata:
            metadata_score = 1.0
            metadata_details = pre_extracted_metadata.copy()

            for flag in pre_extracted_flags:
                if "EDITED_WITH" in flag:
                    metadata_score -= 0.30
                    metadata_details["warning"] = f"Editing software detected: {flag}"
                elif flag == "FILE_MODIFIED_AFTER_CREATION":
                    metadata_score -= 0.10
                    metadata_details["note"] = "Document modified after creation"
                elif flag == "SUSPICIOUSLY_SMALL_FILE":
                    metadata_score -= 0.10

            metadata_score = max(0.0, metadata_score)
            metadata_details["source"] = "pre_extracted"
            logger.debug(f"[{request_id}] Reusing metadata cache, score={metadata_score:.2f}")

            # Run ELA, font, ML in parallel (metadata already done)
            ela_task = asyncio.get_event_loop().run_in_executor(
                None, analyze_ela, document_path, document_type, request_id
            )
            font_task = asyncio.get_event_loop().run_in_executor(
                None, analyze_font_consistency, document_path, document_type
            )
            ml_task = asyncio.get_event_loop().run_in_executor(
                None, analyze_ml_model, document_path, document_type
            )

            (ela_score, ela_details), (font_score, font_details), (ml_score, ml_details) = (
                await asyncio.gather(ela_task, font_task, ml_task)
            )

        else:
            # Run ALL four layers in parallel — nothing pre-extracted
            metadata_task = asyncio.get_event_loop().run_in_executor(
                None, analyze_metadata, document_path
            )
            ela_task = asyncio.get_event_loop().run_in_executor(
                None, analyze_ela, document_path, document_type, request_id
            )
            font_task = asyncio.get_event_loop().run_in_executor(
                None, analyze_font_consistency, document_path, document_type
            )
            ml_task = asyncio.get_event_loop().run_in_executor(
                None, analyze_ml_model, document_path, document_type
            )

            (
                (metadata_score, metadata_details),
                (ela_score, ela_details),
                (font_score, font_details),
                (ml_score, ml_details),
            ) = await asyncio.gather(metadata_task, ela_task, font_task, ml_task)

        # ── Weighted score ──────────────────────────────────────────────────
        weights = {
            "metadata": settings.FORGERY_WEIGHT_METADATA,   # e.g. 0.20
            "ela":      settings.FORGERY_WEIGHT_ELA,         # e.g. 0.30
            "font":     settings.FORGERY_WEIGHT_FONT,        # e.g. 0.20
            "ml":       settings.FORGERY_WEIGHT_ML,          # e.g. 0.30
        }

        forgery_score = (
                metadata_score * weights["metadata"] +
                ela_score      * weights["ela"] +
                font_score     * weights["font"] +
                ml_score       * weights["ml"]
        )

        # ── Verdict ─────────────────────────────────────────────────────────
        if forgery_score > settings.FORGERY_PASS_THRESHOLD:
            forgery_result = "PASS"
        elif forgery_score >= settings.FORGERY_FAIL_THRESHOLD:
            forgery_result = "FLAG"
        else:
            forgery_result = "FAIL"

        # ── Flags ───────────────────────────────────────────────────────────
        flags = list(state.get("flags", []))
        if forgery_result in ["FLAG", "FAIL"]:
            flags.append("FORGERY_FLAG")
            logger.warning(
                f"[{request_id}] Forgery {forgery_result}: score={forgery_score:.2f} "
                f"(meta={metadata_score:.2f}, ela={ela_score:.2f}, "
                f"font={font_score:.2f}, ml={ml_score:.2f})"
            )

        # ── Details ─────────────────────────────────────────────────────────
        forgery_details = {
            "metadata": {"score": round(metadata_score, 4), "details": metadata_details},
            "ela":      {"score": round(ela_score, 4),      "details": ela_details},
            "font":     {"score": round(font_score, 4),     "details": font_details},
            "ml":       {"score": round(ml_score, 4),       "details": ml_details},
            "weights":  weights,
            "used_cached_metadata": bool(pre_extracted_metadata),
            "document_type": document_type,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),   # FIX: not utcnow()
        }

        logger.info(
            f"[{request_id}] Forgery detection complete: "
            f"{forgery_result} (score={forgery_score:.2f})"
        )

        return {
            "forgery_score":   float(forgery_score),
            "forgery_result":  forgery_result,
            "forgery_details": forgery_details,
            "flags":           flags,
            "current_step":    "forgery",
        }

    except Exception as e:
        logger.exception(f"[{request_id}] Forgery detection failed: {e}")

        # FIX: errors default to FLAG (suspicious), not neutral 0.7 that might PASS
        return {
            "forgery_score":   0.0,
            "forgery_result":  "FLAG",
            "forgery_details": {"error": str(e)},
            "flags": state.get("flags", []) + ["FORGERY_CHECK_ERROR"],
            "errors": state.get("errors", []) + [f"Forgery detection failed: {str(e)}"],
            "current_step": "forgery",
        }