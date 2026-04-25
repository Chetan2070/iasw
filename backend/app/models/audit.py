"""
AuditLog Model

Immutable audit trail for all state transitions and actions.
"""

import uuid
import hashlib
import json
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base
from app.models.enums import ActorType, EventType


class AuditLog(Base):
    """
    Immutable audit record for every state transition.

    Each record includes a checksum for tamper detection.
    """

    __tablename__ = "audit_logs"

    # ===================
    # Identity
    # ===================
    audit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(String(36), nullable=False, index=True)

    # ===================
    # Event Details
    # ===================
    event_type = Column(SQLEnum(EventType), nullable=False)
    previous_state = Column(String(50), nullable=True)
    new_state = Column(String(50), nullable=True)

    # ===================
    # Actor Information
    # ===================
    actor_type = Column(SQLEnum(ActorType), nullable=False)
    actor_id = Column(String(50), nullable=False)

    # ===================
    # Agent Information (if AI)
    # ===================
    agent_name = Column(String(50), nullable=True)
    agent_version = Column(String(20), nullable=True)
    llm_model = Column(String(100), nullable=True)

    # ===================
    # Action Details
    # ===================
    action_details = Column(JSON, nullable=True)
    record_snapshot = Column(JSON, nullable=True)  # Full request state at this moment

    # ===================
    # Metadata
    # ===================
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
    checksum = Column(String(64), nullable=False)  # SHA-256 for tamper detection

    def __repr__(self):
        return f"<AuditLog {self.audit_id} - {self.event_type} for {self.request_id}>"

    @staticmethod
    def calculate_checksum(
        request_id: str,
        event_type: str,
        previous_state: str,
        new_state: str,
        actor_type: str,
        actor_id: str,
        timestamp: datetime,
        action_details: dict
    ) -> str:
        """Calculate SHA-256 checksum for tamper detection."""
        data = {
            "request_id": request_id,
            "event_type": event_type,
            "previous_state": previous_state,
            "new_state": new_state,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "timestamp": timestamp.isoformat() if timestamp else None,
            "action_details": action_details,
        }
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    @classmethod
    def create(
        cls,
        request_id: str,
        event_type: EventType,
        actor_type: ActorType,
        actor_id: str,
        previous_state: str = None,
        new_state: str = None,
        agent_name: str = None,
        agent_version: str = None,
        llm_model: str = None,
        action_details: dict = None,
        record_snapshot: dict = None,
    ) -> "AuditLog":
        """Factory method to create audit log with calculated checksum."""
        timestamp = datetime.utcnow()

        checksum = cls.calculate_checksum(
            request_id=request_id,
            event_type=event_type.value,
            previous_state=previous_state,
            new_state=new_state,
            actor_type=actor_type.value,
            actor_id=actor_id,
            timestamp=timestamp,
            action_details=action_details,
        )

        return cls(
            request_id=request_id,
            event_type=event_type,
            previous_state=previous_state,
            new_state=new_state,
            actor_type=actor_type,
            actor_id=actor_id,
            agent_name=agent_name,
            agent_version=agent_version,
            llm_model=llm_model,
            action_details=action_details,
            record_snapshot=record_snapshot,
            timestamp=timestamp,
            checksum=checksum,
        )

    def verify_checksum(self) -> bool:
        """Verify the checksum hasn't been tampered with."""
        expected = self.calculate_checksum(
            request_id=self.request_id,
            event_type=self.event_type.value,
            previous_state=self.previous_state,
            new_state=self.new_state,
            actor_type=self.actor_type.value,
            actor_id=self.actor_id,
            timestamp=self.timestamp,
            action_details=self.action_details,
        )
        return self.checksum == expected
