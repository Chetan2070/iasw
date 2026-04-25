"""
Enums for IASW Application

All enumeration types used across the application.
"""

from enum import Enum


class ChangeType(str, Enum):
    """Types of account changes supported."""
    LEGAL_NAME = "LEGAL_NAME"
    ADDRESS = "ADDRESS"
    DOB = "DOB"
    CONTACT = "CONTACT"


class DocumentType(str, Enum):
    """Types of supporting documents."""
    # For Legal Name Change
    MARRIAGE_CERTIFICATE = "MARRIAGE_CERTIFICATE"
    GAZETTE_NOTIFICATION = "GAZETTE_NOTIFICATION"
    DEED_POLL = "DEED_POLL"
    COURT_ORDER = "COURT_ORDER"

    # For Address Change
    UTILITY_BILL = "UTILITY_BILL"
    LEASE_AGREEMENT = "LEASE_AGREEMENT"

    # For DOB Change
    BIRTH_CERTIFICATE = "BIRTH_CERTIFICATE"
    PASSPORT = "PASSPORT"
    PAN_CARD = "PAN_CARD"

    # For Contact Change
    CONSENT_FORM = "CONSENT_FORM"


class RequestStatus(str, Enum):
    """Status of a change request through the workflow."""
    INTAKE_RECEIVED = "INTAKE_RECEIVED"
    VALIDATED = "VALIDATED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    AI_VERIFIED_PENDING_HUMAN = "AI_VERIFIED_PENDING_HUMAN"
    IN_REVIEW = "IN_REVIEW"
    PENDING_INFO = "PENDING_INFO"
    ESCALATED = "ESCALATED"
    REPROCESSING = "REPROCESSING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RiskTier(str, Enum):
    """Risk classification for requests."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ForgeryResult(str, Enum):
    """Result of forgery detection."""
    PASS = "PASS"
    FLAG = "FLAG"
    FAIL = "FAIL"


class Recommendation(str, Enum):
    """AI recommendation for the request."""
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class Decision(str, Enum):
    """Checker's decision on a request."""
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MORE_INFO = "MORE_INFO"
    ESCALATE = "ESCALATE"


class ActorType(str, Enum):
    """Type of actor performing an action."""
    SYSTEM = "SYSTEM"
    HUMAN = "HUMAN"
    AI_AGENT = "AI_AGENT"


class EventType(str, Enum):
    """Type of audit log event."""
    STATE_CHANGE = "STATE_CHANGE"
    HUMAN_ACTION = "HUMAN_ACTION"
    SYSTEM_EVENT = "SYSTEM_EVENT"
    ERROR = "ERROR"


# Document type mappings - which documents are allowed for which change type
ALLOWED_DOCUMENTS = {
    ChangeType.LEGAL_NAME: [
        DocumentType.MARRIAGE_CERTIFICATE,
        DocumentType.GAZETTE_NOTIFICATION,
        DocumentType.DEED_POLL,
        DocumentType.COURT_ORDER,
    ],
    ChangeType.ADDRESS: [
        DocumentType.UTILITY_BILL,
        DocumentType.LEASE_AGREEMENT,
        DocumentType.PASSPORT,
    ],
    ChangeType.DOB: [
        DocumentType.BIRTH_CERTIFICATE,
        DocumentType.PASSPORT,
        DocumentType.PAN_CARD,
    ],
    ChangeType.CONTACT: [
        DocumentType.CONSENT_FORM,
    ],
}


def is_document_allowed(change_type: ChangeType, document_type: DocumentType) -> bool:
    """Check if a document type is allowed for a change type."""
    allowed = ALLOWED_DOCUMENTS.get(change_type, [])
    return document_type in allowed
