"""
Document Metadata Analysis Node

Extracts and analyzes file metadata from documents.
Runs in parallel with OCR for efficiency.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.agents.state import ProcessingState

logger = logging.getLogger(__name__)


def extract_image_metadata(file_path: str) -> Dict[str, Any]:
    """Extract EXIF and other metadata from image files."""
    metadata = {}

    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        with Image.open(file_path) as img:
            metadata["format"] = img.format
            metadata["mode"] = img.mode
            metadata["size"] = {"width": img.width, "height": img.height}

            # Extract EXIF data if available
            exif_data = img._getexif()
            if exif_data:
                exif = {}
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if isinstance(value, bytes):
                        continue  # Skip binary data
                    exif[tag] = str(value)
                metadata["exif"] = exif

                # Check for editing software signatures
                if "Software" in exif:
                    metadata["editing_software"] = exif["Software"]
                if "ProcessingSoftware" in exif:
                    metadata["processing_software"] = exif["ProcessingSoftware"]

    except Exception as e:
        logger.debug(f"Could not extract image metadata: {e}")

    return metadata


def extract_pdf_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from PDF files."""
    metadata = {}

    try:
        import fitz  # PyMuPDF

        doc = fitz.open(file_path)
        metadata["page_count"] = doc.page_count

        # PDF metadata
        pdf_meta = doc.metadata
        if pdf_meta:
            metadata["title"] = pdf_meta.get("title", "")
            metadata["author"] = pdf_meta.get("author", "")
            metadata["creator"] = pdf_meta.get("creator", "")
            metadata["producer"] = pdf_meta.get("producer", "")
            metadata["creation_date"] = pdf_meta.get("creationDate", "")
            metadata["mod_date"] = pdf_meta.get("modDate", "")

            # Check for editing software signatures
            if pdf_meta.get("producer"):
                metadata["editing_software"] = pdf_meta.get("producer")
            if pdf_meta.get("creator"):
                metadata["creator_software"] = pdf_meta.get("creator")

        doc.close()

    except Exception as e:
        logger.debug(f"Could not extract PDF metadata: {e}")

    return metadata


def analyze_metadata_flags(metadata: Dict[str, Any], file_stats: Dict[str, Any]) -> List[str]:
    """
    Analyze metadata for suspicious patterns.

    Returns list of flags indicating potential issues.
    """
    flags = []

    # Check for known editing software
    editing_software_signatures = [
        "photoshop", "gimp", "paint", "acrobat",
        "foxit", "nitro", "pdf-xchange", "illustrator"
    ]

    software_fields = [
        metadata.get("editing_software", ""),
        metadata.get("processing_software", ""),
        metadata.get("creator_software", ""),
    ]

    for software in software_fields:
        if software:
            software_lower = software.lower()
            for sig in editing_software_signatures:
                if sig in software_lower:
                    flags.append(f"EDITED_WITH_{sig.upper()}")
                    break

    # Check if file was recently created (within 24 hours)
    if file_stats.get("created_at"):
        try:
            created = datetime.fromisoformat(file_stats["created_at"])
            if (datetime.utcnow() - created).total_seconds() < 86400:
                flags.append("FILE_CREATED_RECENTLY")
        except (ValueError, TypeError):
            pass

    # Check for modification after creation
    if file_stats.get("created_at") and file_stats.get("modified_at"):
        try:
            created = datetime.fromisoformat(file_stats["created_at"])
            modified = datetime.fromisoformat(file_stats["modified_at"])
            if modified > created:
                flags.append("FILE_MODIFIED_AFTER_CREATION")
        except (ValueError, TypeError):
            pass

    # Check for very small file size (potentially fake)
    if file_stats.get("size_bytes", 0) < 10000:  # Less than 10KB
        flags.append("SUSPICIOUSLY_SMALL_FILE")

    return flags


async def metadata_node(state: ProcessingState) -> Dict[str, Any]:
    """
    Analyze document metadata.

    This node runs in PARALLEL with OCR to improve processing time.
    It extracts file metadata, EXIF data, and checks for editing software signatures.

    Input State:
        - document_path: path to the document file

    Output State Updates:
        - file_metadata: dict with extracted metadata
        - file_stats: dict with file system stats
        - metadata_flags: list of suspicious patterns found
        - current_step: "metadata" (but may be overwritten by parallel OCR)
    """
    request_id = state.get('request_id', 'unknown')
    document_path = state.get('document_path', '')

    logger.info(f"[{request_id}] Analyzing document metadata")

    result = {
        "file_metadata": {},
        "file_stats": {},
        "metadata_flags": [],
    }

    try:
        if not os.path.exists(document_path):
            logger.warning(f"[{request_id}] Document not found: {document_path}")
            return result

        # Get file system stats
        stat = os.stat(document_path)
        file_stats = {
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "accessed_at": datetime.fromtimestamp(stat.st_atime).isoformat(),
        }
        result["file_stats"] = file_stats

        # Determine file type and extract appropriate metadata
        ext = os.path.splitext(document_path)[1].lower()

        if ext == '.pdf':
            result["file_metadata"] = extract_pdf_metadata(document_path)
        elif ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp']:
            result["file_metadata"] = extract_image_metadata(document_path)
        else:
            result["file_metadata"] = {"format": ext.lstrip('.')}

        # Analyze for suspicious patterns
        result["metadata_flags"] = analyze_metadata_flags(
            result["file_metadata"],
            result["file_stats"]
        )

        logger.info(
            f"[{request_id}] Metadata analysis complete: "
            f"{len(result['metadata_flags'])} flags found"
        )

    except Exception as e:
        logger.exception(f"[{request_id}] Metadata analysis failed")
        result["errors"] = state.get('errors', []) + [f"Metadata analysis failed: {str(e)}"]

    return result
