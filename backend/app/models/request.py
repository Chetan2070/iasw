"""
PendingRequest Model

Core entity representing a change request in the system.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Text, Numeric, DateTime, Integer, JSON, Enum as SQLEnum
from sqlalchemy.sql import func

from app.db.session import Base
from app.models.enums import (
    ChangeType, DocumentType, RequestStatus, RiskTier,
    ForgeryResult, Recommendation, Decision
)


class PendingRequest(Base):
    """
    Represents a change request in the pending table.

    This is the core entity that tracks a request through the entire
    workflow from intake to completion.
    """

    __tablename__ = "pending_requests"

    # ===================
    # Identity
    # ===================
    request_id = Column(String(36), primary_key=True, index=True)
    idempotency_key = Column(String(64), unique=True, index=True)
    customer_id = Column(String(20), nullable=False, index=True)

    # ===================
    # Request Details
    # ===================
    change_type = Column(SQLEnum(ChangeType), nullable=False)
    document_type = Column(SQLEnum(DocumentType), nullable=False)

    # ===================
    # Requested Values
    # ===================
    requested_old_value = Column(String(255), nullable=False)
    requested_new_value = Column(String(255), nullable=False)

    # ===================
    # Extracted Values (from document)
    # ===================
    extracted_old_value = Column(String(255), nullable=True)
    extracted_new_value = Column(String(255), nullable=True)
    extraction_metadata = Column(JSON, nullable=True)  # All extracted fields with confidence

    # ===================
    # Confidence Scores (per field)
    # ===================
    old_name_match_score = Column(Numeric(5, 4), nullable=True)
    new_name_match_score = Column(Numeric(5, 4), nullable=True)
    ocr_confidence = Column(Numeric(5, 4), nullable=True)
    extraction_confidence = Column(Numeric(5, 4), nullable=True)
    doc_authenticity_score = Column(Numeric(5, 4), nullable=True)
    overall_confidence = Column(Numeric(5, 4), nullable=True)

    # ===================
    # Forgery Detection
    # ===================
    forgery_score = Column(Numeric(5, 4), nullable=True)
    forgery_result = Column(SQLEnum(ForgeryResult), nullable=True)
    forgery_details = Column(JSON, nullable=True)  # Per-layer breakdown

    # ===================
    # Risk & Routing
    # ===================
    risk_tier = Column(SQLEnum(RiskTier), nullable=True)
    flags = Column(JSON, default=list)  # Array of flag codes
    ai_recommendation = Column(SQLEnum(Recommendation), nullable=True)
    ai_summary = Column(Text, nullable=True)

    # ===================
    # Document Storage
    # ===================
    document_storage_path = Column(String(255), nullable=True)
    filenet_staging_id = Column(String(100), nullable=True)
    filenet_permanent_id = Column(String(100), nullable=True)

    # ===================
    # Workflow Status
    # ===================
    status = Column(SQLEnum(RequestStatus), nullable=False, default=RequestStatus.INTAKE_RECEIVED, index=True)
    assigned_checker = Column(String(50), nullable=True, index=True)
    checker_lock_until = Column(DateTime, nullable=True)
    checker_decision = Column(SQLEnum(Decision), nullable=True)
    checker_decision_reason = Column(Text, nullable=True)

    # ===================
    # Resubmit Tracking
    # ===================
    resubmit_count = Column(Integer, default=0)
    max_resubmits = Column(Integer, default=3)
    original_request_id = Column(String(36), nullable=True)

    # ===================
    # Timestamps
    # ===================
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    validated_at = Column(DateTime, nullable=True)
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    staged_at = Column(DateTime, nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # ===================
    # Audit
    # ===================
    created_by = Column(String(50), nullable=True)
    last_updated_at = Column(DateTime, onupdate=func.now())
    last_updated_by = Column(String(50), nullable=True)

    def __repr__(self):
        return f"<PendingRequest {self.request_id} - {self.status}>"

    @property
    def is_locked(self) -> bool:
        """Check if request is currently locked by a checker."""
        if not self.checker_lock_until:
            return False
        return datetime.utcnow() < self.checker_lock_until

    @property
    def can_be_claimed(self) -> bool:
        """Check if request can be claimed by a checker."""
        claimable_statuses = [
            RequestStatus.AI_VERIFIED_PENDING_HUMAN,
        ]
        return self.status in claimable_statuses and not self.is_locked

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "request_id": self.request_id,
            "customer_id": self.customer_id,
            "change_type": self.change_type.value if self.change_type else None,
            "document_type": self.document_type.value if self.document_type else None,
            "requested_old_value": self.requested_old_value,
            "requested_new_value": self.requested_new_value,
            "extracted_old_value": self.extracted_old_value,
            "extracted_new_value": self.extracted_new_value,
            "overall_confidence": float(self.overall_confidence) if self.overall_confidence else None,
            "risk_tier": self.risk_tier.value if self.risk_tier else None,
            "flags": self.flags or [],
            "ai_recommendation": self.ai_recommendation.value if self.ai_recommendation else None,
            "ai_summary": self.ai_summary,
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
