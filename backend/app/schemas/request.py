"""
Request Schemas

Pydantic schemas for request validation and serialization.
"""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator

from app.models.enums import (
    ChangeType, DocumentType, RequestStatus, RiskTier,
    ForgeryResult, Recommendation, Decision
)


# ===================
# Create Request
# ===================

class CreateRequestSchema(BaseModel):
    """Schema for creating a new change request."""

    account_number: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Bank account number"
    )
    change_type: ChangeType = Field(
        ...,
        description="Type of change requested"
    )
    document_type: DocumentType = Field(
        ...,
        description="Type of supporting document"
    )
    current_value: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Current value (e.g., current name)"
    )
    new_value: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Requested new value"
    )

    @field_validator("new_value")
    @classmethod
    def new_value_different(cls, v, info):
        """Ensure new value is different from current value."""
        if "current_value" in info.data and v == info.data["current_value"]:
            raise ValueError("New value must be different from current value")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "account_number": "1234567890",
                "change_type": "LEGAL_NAME",
                "document_type": "MARRIAGE_CERTIFICATE",
                "current_value": "Priya Sharma",
                "new_value": "Priya Mehta"
            }
        }


# ===================
# Request Response
# ===================

class RequestResponse(BaseModel):
    """Response after creating a request."""

    request_id: str
    status: RequestStatus
    message: str
    customer_name: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "REQ-12345",
                "status": "VALIDATED",
                "message": "Request created successfully. Please upload supporting document.",
                "customer_name": "Priya Sharma"
            }
        }


# ===================
# Request Summary (for list view)
# ===================

class RequestSummary(BaseModel):
    """Summary view of a request for list displays."""

    request_id: str
    customer_id: str
    change_type: ChangeType
    document_type: DocumentType
    status: RequestStatus
    risk_tier: Optional[RiskTier] = None
    ai_recommendation: Optional[Recommendation] = None
    overall_confidence: Optional[float] = None
    flags: List[str] = []
    created_at: datetime
    time_in_current_status_minutes: Optional[int] = None


# ===================
# Request Detail (full view)
# ===================

class ExtractionDetail(BaseModel):
    """Details of a single extracted field."""

    field_name: str
    value: str
    confidence: float
    source_snippet: Optional[str] = None


class ForgeryDetail(BaseModel):
    """Forgery detection details."""

    score: float
    result: ForgeryResult
    metadata_score: Optional[float] = None
    ela_score: Optional[float] = None
    font_score: Optional[float] = None
    ml_score: Optional[float] = None


class ConfidenceBreakdown(BaseModel):
    """Breakdown of confidence scores."""

    old_name_match: Optional[float] = None
    new_name_match: Optional[float] = None
    ocr_confidence: Optional[float] = None
    extraction_confidence: Optional[float] = None
    doc_authenticity: Optional[float] = None
    overall: Optional[float] = None


class RequestDetail(BaseModel):
    """Full request details for viewing."""

    # Identity
    request_id: str
    idempotency_key: Optional[str] = None
    customer_id: str

    # Request details
    change_type: ChangeType
    document_type: DocumentType
    requested_old_value: str
    requested_new_value: str

    # Extracted values
    extracted_old_value: Optional[str] = None
    extracted_new_value: Optional[str] = None
    extraction_details: List[ExtractionDetail] = []

    # Confidence scores
    confidence: Optional[ConfidenceBreakdown] = None

    # Forgery detection
    forgery: Optional[ForgeryDetail] = None

    # Risk and routing
    risk_tier: Optional[RiskTier] = None
    flags: List[str] = []
    ai_recommendation: Optional[Recommendation] = None
    ai_summary: Optional[str] = None

    # Document storage
    document_storage_path: Optional[str] = None
    filenet_staging_id: Optional[str] = None
    filenet_permanent_id: Optional[str] = None

    # Workflow status
    status: RequestStatus
    assigned_checker: Optional[str] = None
    checker_decision: Optional[Decision] = None
    checker_decision_reason: Optional[str] = None

    # Timestamps
    created_at: datetime
    validated_at: Optional[datetime] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    staged_at: Optional[datetime] = None
    claimed_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Computed fields
    is_locked: bool = False
    can_be_claimed: bool = False
    time_in_current_status_minutes: Optional[int] = None


# ===================
# Upload Response
# ===================

class UploadResponse(BaseModel):
    """Response after uploading a document."""

    request_id: str
    status: RequestStatus
    document_id: str
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "REQ-12345",
                "status": "QUEUED",
                "document_id": "DOC-67890",
                "message": "Document uploaded. Processing will begin shortly."
            }
        }


# ===================
# Request Filters
# ===================

class RequestFilters(BaseModel):
    """Filters for listing requests."""

    customer_id: Optional[str] = None
    change_type: Optional[ChangeType] = None
    status: Optional[RequestStatus] = None
    risk_tier: Optional[RiskTier] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


# ===================
# Paginated Response
# ===================

class PaginatedRequests(BaseModel):
    """Paginated list of requests."""

    items: List[RequestSummary]
    total: int
    page: int
    limit: int
    pages: int
