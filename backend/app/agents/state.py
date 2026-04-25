"""
LangGraph State Definition

Defines the state that flows through the document processing pipeline.
"""

from typing import TypedDict, List, Optional, Any
from datetime import datetime


class ProcessingState(TypedDict, total=False):
    """
    State that flows through the LangGraph pipeline.

    This TypedDict defines all fields that can be passed between nodes.
    Each node reads from and writes to this shared state.
    """
   
    # Input (from request)
    
    request_id: str
    customer_id: str
    change_type: str
    document_type: str
    requested_old_value: str
    requested_new_value: str
    document_path: str

   
    # Validation Output
   
    validation_passed: bool
    validation_errors: List[str]

   
    # OCR Output

    ocr_text: str
    ocr_confidence: float
    ocr_word_confidences: List[dict]
    ocr_method: str  # "tesseract" or "google_vision"
    ocr_pages_processed: int


    # Metadata Analysis Output (runs in parallel with OCR)

    file_metadata: dict  # EXIF, PDF metadata, etc.
    file_stats: dict  # File system stats (size, dates)
    metadata_flags: List[str]  # Suspicious patterns found

   
    # Classification Output
   
    detected_document_type: str
    classification_confidence: float
    classification_match: bool
    classification_signals: List[str]

   
    # Extraction Output
   
    extracted_fields: dict  # {field_name: {value, confidence, source_snippet}}
    extraction_confidence: float
    extracted_old_value: str
    extracted_new_value: str

   
    # Forgery Detection Output
   
    forgery_score: float  # 0.0 (forged) to 1.0 (authentic)
    forgery_result: str  # PASS, FLAG, FAIL
    forgery_details: dict  # Per-layer breakdown

   
    # Scoring Output
   
    old_name_match_score: float
    new_name_match_score: float
    field_scores: List[dict]
    overall_score: float
    risk_tier: str  # LOW, MEDIUM, HIGH

   
    # Summary Output
   
    ai_summary: str
    ai_recommendation: str  # APPROVE, REJECT, MANUAL_REVIEW

   
    # Flags (accumulated through pipeline)
   
    flags: List[str]

   
    # Processing Metadata
   
    current_step: str
    processing_started_at: str
    processing_completed_at: str
    errors: List[str]
    llm_calls: List[dict]  # Track LLM usage


def create_initial_state(
    request_id: str,
    customer_id: str,
    change_type: str,
    document_type: str,
    requested_old_value: str,
    requested_new_value: str,
    document_path: str,
) -> ProcessingState:
    """Create initial state for a new processing run."""
    return ProcessingState(
        request_id=request_id,
        customer_id=customer_id,
        change_type=change_type,
        document_type=document_type,
        requested_old_value=requested_old_value,
        requested_new_value=requested_new_value,
        document_path=document_path,
        validation_passed=False,
        validation_errors=[],
        ocr_text="",
        ocr_confidence=0.0,
        ocr_word_confidences=[],
        ocr_method="",
        ocr_pages_processed=0,
        file_metadata={},
        file_stats={},
        metadata_flags=[],
        detected_document_type="",
        classification_confidence=0.0,
        classification_match=False,
        classification_signals=[],
        extracted_fields={},
        extraction_confidence=0.0,
        extracted_old_value="",
        extracted_new_value="",
        forgery_score=0.0,
        forgery_result="",
        forgery_details={},
        old_name_match_score=0.0,
        new_name_match_score=0.0,
        field_scores=[],
        overall_score=0.0,
        risk_tier="",
        ai_summary="",
        ai_recommendation="",
        flags=[],
        current_step="init",
        processing_started_at=datetime.utcnow().isoformat(),
        processing_completed_at="",
        errors=[],
        llm_calls=[],
    )
