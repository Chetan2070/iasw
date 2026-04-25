"""
Checker Schemas

Pydantic schemas for checker operations.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.enums import (
    ChangeType, DocumentType, RequestStatus, RiskTier,
    Recommendation, Decision
)


# ===================
# Queue Item
# ===================

class QueueItem(BaseModel):
    """Item in the checker queue."""

    request_id: str
    customer_id: str
    change_type: ChangeType
    document_type: DocumentType
    risk_tier: RiskTier
    ai_recommendation: Recommendation
    overall_score: float
    flags: List[str] = []
    queued_at: datetime
    time_in_queue_minutes: int

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "REQ-12345",
                "customer_id": "C001",
                "change_type": "LEGAL_NAME",
                "document_type": "MARRIAGE_CERTIFICATE",
                "risk_tier": "LOW",
                "ai_recommendation": "APPROVE",
                "overall_score": 0.946,
                "flags": [],
                "queued_at": "2024-03-20T10:30:48Z",
                "time_in_queue_minutes": 15
            }
        }


# ===================
# Queue Response
# ===================

class QueueResponse(BaseModel):
    """Response for queue listing."""

    items: List[QueueItem]
    total: int
    page: int
    limit: int


# ===================
# Queue Filters
# ===================

class QueueFilters(BaseModel):
    """Filters for the checker queue."""

    risk_tier: Optional[RiskTier] = None
    ai_recommendation: Optional[Recommendation] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


# ===================
# Claim Request/Response
# ===================

class ClaimResponse(BaseModel):
    """Response after claiming a request."""

    request_id: str
    status: str
    assigned_to: str
    lock_expires_at: datetime
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "REQ-12345",
                "status": "IN_REVIEW",
                "assigned_to": "checker_jane",
                "lock_expires_at": "2024-03-20T11:45:00Z",
                "message": "Request claimed successfully. You have 15 minutes to review."
            }
        }


# ===================
# Decision Request/Response
# ===================

class DecisionRequest(BaseModel):
    """Request body for submitting a decision."""

    decision: Decision
    reason: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Required for REJECT, MORE_INFO, and ESCALATE"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "decision": "APPROVE",
                "reason": None
            }
        }


class DecisionResponse(BaseModel):
    """Response after submitting a decision."""

    request_id: str
    decision: Decision
    new_status: RequestStatus
    rps_updated: bool
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "REQ-12345",
                "decision": "APPROVE",
                "new_status": "APPROVED",
                "rps_updated": True,
                "message": "Decision recorded. Core banking updated successfully."
            }
        }


# ===================
# Release Response
# ===================

class ReleaseResponse(BaseModel):
    """Response after releasing a claimed request."""

    request_id: str
    status: str
    message: str


# ===================
# Review Data (for UI)
# ===================

class FieldScore(BaseModel):
    """Score for a single field."""

    field_name: str
    extracted_value: str
    expected_value: str
    match_score: float = Field(..., ge=0.0, le=1.0)
    match_method: str = "jaro_winkler"


class ReviewData(BaseModel):
    """Complete review data for the checker UI."""

    # Request info
    request_id: str
    customer_id: str
    change_type: ChangeType
    document_type: DocumentType

    # Values
    requested_old_value: str
    requested_new_value: str
    extracted_old_value: Optional[str] = None
    extracted_new_value: Optional[str] = None

    # Scores
    field_scores: List[FieldScore] = []
    ocr_confidence: Optional[float] = None
    extraction_confidence: Optional[float] = None
    doc_authenticity_score: Optional[float] = None
    overall_score: Optional[float] = None

    # Forgery
    forgery_score: Optional[float] = None
    forgery_result: Optional[str] = None
    forgery_details: Optional[dict] = None

    # Risk and recommendation
    risk_tier: Optional[RiskTier] = None
    flags: List[str] = []
    ai_recommendation: Optional[Recommendation] = None
    ai_summary: Optional[str] = None

    # Document
    document_url: Optional[str] = None
    filenet_reference: Optional[str] = None

    # Timestamps
    created_at: datetime
    staged_at: Optional[datetime] = None
    claimed_at: Optional[datetime] = None
    assigned_checker: Optional[str] = None
