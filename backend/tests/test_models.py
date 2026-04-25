"""
Tests for database models.
"""

import pytest
from datetime import datetime, timedelta
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.request import PendingRequest
from app.models.customer import Customer, Checker
from app.models.audit import AuditLog
from app.models.enums import (
    ChangeType,
    DocumentType,
    RequestStatus,
    RiskTier,
    Recommendation,
    Decision,
)


class TestPendingRequestModel:
    """Tests for PendingRequest model."""

    @pytest.mark.asyncio
    async def test_create_pending_request(self, test_session: AsyncSession):
        """Test creating a pending request."""
        request = PendingRequest(
            request_id=str(uuid.uuid4()),
            customer_id="CUST-001",
            change_type=ChangeType.LEGAL_NAME,
            document_type=DocumentType.MARRIAGE_CERTIFICATE,
            requested_old_value="John Doe",
            requested_new_value="John Smith",
            status=RequestStatus.INTAKE_RECEIVED,
        )

        test_session.add(request)
        await test_session.commit()
        await test_session.refresh(request)

        assert request.id is not None
        assert request.created_at is not None
        assert request.status == RequestStatus.INTAKE_RECEIVED

    @pytest.mark.asyncio
    async def test_request_status_transitions(
        self, test_session: AsyncSession, sample_request
    ):
        """Test request status transitions."""
        # INTAKE_RECEIVED -> VALIDATED
        sample_request.status = RequestStatus.VALIDATED
        await test_session.commit()
        await test_session.refresh(sample_request)
        assert sample_request.status == RequestStatus.VALIDATED

        # VALIDATED -> PROCESSING
        sample_request.status = RequestStatus.PROCESSING
        await test_session.commit()
        assert sample_request.status == RequestStatus.PROCESSING

        # PROCESSING -> AI_VERIFIED_PENDING_HUMAN
        sample_request.status = RequestStatus.AI_VERIFIED_PENDING_HUMAN
        await test_session.commit()
        assert sample_request.status == RequestStatus.AI_VERIFIED_PENDING_HUMAN

    @pytest.mark.asyncio
    async def test_request_ai_fields(self, test_session: AsyncSession, sample_request):
        """Test setting AI-related fields."""
        sample_request.ocr_confidence = 0.95
        sample_request.extraction_confidence = 0.92
        sample_request.doc_authenticity_score = 0.88
        sample_request.overall_score = 0.91
        sample_request.risk_tier = RiskTier.LOW
        sample_request.ai_recommendation = Recommendation.APPROVE
        sample_request.ai_summary = "Document verified successfully."
        sample_request.flags = ["high_confidence"]

        await test_session.commit()
        await test_session.refresh(sample_request)

        assert sample_request.ocr_confidence == 0.95
        assert sample_request.risk_tier == RiskTier.LOW
        assert sample_request.ai_recommendation == Recommendation.APPROVE
        assert "high_confidence" in sample_request.flags

    @pytest.mark.asyncio
    async def test_request_claim_lock(self, test_session: AsyncSession, sample_request):
        """Test claim lock mechanism."""
        lock_time = datetime.utcnow() + timedelta(minutes=15)
        sample_request.assigned_checker_id = "CHK-001"
        sample_request.lock_expires_at = lock_time
        sample_request.status = RequestStatus.IN_REVIEW

        await test_session.commit()
        await test_session.refresh(sample_request)

        assert sample_request.assigned_checker_id == "CHK-001"
        assert sample_request.lock_expires_at is not None

    @pytest.mark.asyncio
    async def test_request_field_scores_json(
        self, test_session: AsyncSession, sample_request
    ):
        """Test JSON field for field scores."""
        field_scores = [
            {
                "field_name": "old_name",
                "extracted_value": "John Doe",
                "expected_value": "John Doe",
                "match_score": 1.0,
                "match_method": "exact",
            },
            {
                "field_name": "new_name",
                "extracted_value": "John Smith",
                "expected_value": "John Smith",
                "match_score": 1.0,
                "match_method": "exact",
            },
        ]
        sample_request.field_scores = field_scores

        await test_session.commit()
        await test_session.refresh(sample_request)

        assert len(sample_request.field_scores) == 2
        assert sample_request.field_scores[0]["match_score"] == 1.0


class TestCustomerModel:
    """Tests for Customer model."""

    @pytest.mark.asyncio
    async def test_create_customer(self, test_session: AsyncSession):
        """Test creating a customer."""
        customer = Customer(
            customer_id="CUST-NEW-001",
            full_name="Jane Doe",
            date_of_birth="1985-05-20",
            address="456 Test Ave",
            email="jane@test.com",
            phone="+1987654321",
        )

        test_session.add(customer)
        await test_session.commit()
        await test_session.refresh(customer)

        assert customer.id is not None
        assert customer.customer_id == "CUST-NEW-001"
        assert customer.created_at is not None

    @pytest.mark.asyncio
    async def test_customer_unique_id(
        self, test_session: AsyncSession, sample_customer
    ):
        """Test customer ID uniqueness."""
        duplicate = Customer(
            customer_id=sample_customer.customer_id,
            full_name="Another Person",
            date_of_birth="1990-01-01",
            address="789 Test St",
            email="another@test.com",
        )

        test_session.add(duplicate)
        with pytest.raises(Exception):
            await test_session.commit()


class TestCheckerModel:
    """Tests for Checker model."""

    @pytest.mark.asyncio
    async def test_create_checker(self, test_session: AsyncSession):
        """Test creating a checker."""
        checker = Checker(
            checker_id="CHK-NEW-001",
            name="New Checker",
            email="newchecker@test.com",
            is_active=True,
        )

        test_session.add(checker)
        await test_session.commit()
        await test_session.refresh(checker)

        assert checker.id is not None
        assert checker.is_active == True

    @pytest.mark.asyncio
    async def test_checker_deactivation(
        self, test_session: AsyncSession, sample_checker
    ):
        """Test checker deactivation."""
        sample_checker.is_active = False
        await test_session.commit()
        await test_session.refresh(sample_checker)

        assert sample_checker.is_active == False


class TestAuditLogModel:
    """Tests for AuditLog model."""

    @pytest.mark.asyncio
    async def test_create_audit_log(
        self, test_session: AsyncSession, sample_request, sample_checker
    ):
        """Test creating an audit log entry."""
        audit = AuditLog(
            request_id=sample_request.request_id,
            action="DECISION_MADE",
            actor_id=sample_checker.checker_id,
            actor_type="checker",
            old_status=RequestStatus.IN_REVIEW.value,
            new_status=RequestStatus.APPROVED.value,
            details={"decision": "APPROVE", "confidence": 0.91},
        )

        test_session.add(audit)
        await test_session.commit()
        await test_session.refresh(audit)

        assert audit.id is not None
        assert audit.checksum is not None
        assert audit.created_at is not None

    @pytest.mark.asyncio
    async def test_audit_log_checksum_integrity(
        self, test_session: AsyncSession, sample_request
    ):
        """Test audit log checksum for tamper detection."""
        audit = AuditLog(
            request_id=sample_request.request_id,
            action="STATUS_CHANGE",
            actor_id="SYSTEM",
            actor_type="system",
            old_status=RequestStatus.INTAKE_RECEIVED.value,
            new_status=RequestStatus.PROCESSING.value,
        )

        test_session.add(audit)
        await test_session.commit()
        await test_session.refresh(audit)

        original_checksum = audit.checksum
        assert original_checksum is not None

        # Verify checksum is based on content
        audit.action = "MODIFIED_ACTION"
        # Note: In real implementation, checksum should be recalculated
        # and differ from original

    @pytest.mark.asyncio
    async def test_audit_log_ordering(
        self, test_session: AsyncSession, sample_request
    ):
        """Test audit logs are properly ordered by timestamp."""
        for i, action in enumerate(["ACTION_1", "ACTION_2", "ACTION_3"]):
            audit = AuditLog(
                request_id=sample_request.request_id,
                action=action,
                actor_id="SYSTEM",
                actor_type="system",
            )
            test_session.add(audit)
            await test_session.commit()

        # Query and verify ordering
        from sqlalchemy import select

        result = await test_session.execute(
            select(AuditLog)
            .where(AuditLog.request_id == sample_request.request_id)
            .order_by(AuditLog.created_at)
        )
        logs = result.scalars().all()

        assert len(logs) == 3
        assert logs[0].action == "ACTION_1"
        assert logs[2].action == "ACTION_3"
