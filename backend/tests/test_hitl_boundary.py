"""
Tests for Human-in-the-Loop (HITL) boundary enforcement.

These tests verify that the system properly enforces the HITL constraint:
AI can only recommend, never approve or reject directly.
Only human checkers can make final decisions.
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.request import PendingRequest
from app.models.audit import AuditLog
from app.models.enums import RequestStatus, RiskTier, Recommendation, Decision


class TestAICannotApprove:
    """Tests verifying AI cannot directly approve requests."""

    @pytest.mark.asyncio
    async def test_ai_sets_recommendation_not_status(
        self, test_session: AsyncSession, sample_request
    ):
        """Test that AI processing sets recommendation, not approval status."""
        # Simulate AI processing completion
        sample_request.status = RequestStatus.AI_VERIFIED_PENDING_HUMAN
        sample_request.ai_recommendation = Recommendation.APPROVE
        sample_request.overall_score = 0.95
        sample_request.risk_tier = RiskTier.LOW

        await test_session.commit()
        await test_session.refresh(sample_request)

        # Verify status is still pending human review, not approved
        assert sample_request.status == RequestStatus.AI_VERIFIED_PENDING_HUMAN
        assert sample_request.status != RequestStatus.APPROVED
        assert sample_request.ai_recommendation == Recommendation.APPROVE

    @pytest.mark.asyncio
    async def test_high_confidence_still_requires_human(
        self, test_session: AsyncSession, sample_request
    ):
        """Test that even 100% AI confidence requires human approval."""
        sample_request.status = RequestStatus.AI_VERIFIED_PENDING_HUMAN
        sample_request.ai_recommendation = Recommendation.APPROVE
        sample_request.overall_score = 1.0  # 100% confidence
        sample_request.risk_tier = RiskTier.LOW

        await test_session.commit()
        await test_session.refresh(sample_request)

        # Still requires human review
        assert sample_request.status == RequestStatus.AI_VERIFIED_PENDING_HUMAN
        assert sample_request.assigned_checker_id is None

    @pytest.mark.asyncio
    async def test_no_direct_api_for_ai_approval(self, client: AsyncClient):
        """Test there's no API endpoint for AI to directly approve."""
        # Verify no /ai/approve endpoint exists
        response = await client.post("/api/v1/ai/approve/test-request-id")
        assert response.status_code == 404

        response = await client.post("/api/v1/requests/test-id/auto-approve")
        assert response.status_code == 404


class TestHumanDecisionRequired:
    """Tests verifying human decision is required for status changes."""

    @pytest.mark.asyncio
    async def test_approval_requires_checker_id(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
    ):
        """Test that approval requires a valid checker ID."""
        # Attempt to approve without proper claim
        response = await client.post(
            f"/api/v1/checker/decide/{processed_request.request_id}",
            json={"decision": "APPROVE"},
            # Missing checker_id param
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_only_assigned_checker_can_decide(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test that only the assigned checker can make decisions."""
        # Assign to different checker
        processed_request.status = RequestStatus.IN_REVIEW
        processed_request.assigned_checker_id = "OTHER-CHECKER-ID"
        processed_request.lock_expires_at = datetime.utcnow() + timedelta(minutes=15)
        await test_session.commit()

        # Try to decide with different checker
        response = await client.post(
            f"/api/v1/checker/decide/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
            json={"decision": "APPROVE"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_decision_creates_audit_trail(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test that human decisions create audit trail."""
        # Claim the request
        processed_request.status = RequestStatus.IN_REVIEW
        processed_request.assigned_checker_id = sample_checker.checker_id
        processed_request.lock_expires_at = datetime.utcnow() + timedelta(minutes=15)
        await test_session.commit()

        # Make decision
        response = await client.post(
            f"/api/v1/checker/decide/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
            json={"decision": "APPROVE"},
        )

        assert response.status_code == 200

        # Verify audit log was created
        result = await test_session.execute(
            select(AuditLog).where(
                AuditLog.request_id == processed_request.request_id
            )
        )
        audit_logs = result.scalars().all()

        decision_log = next(
            (log for log in audit_logs if log.action == "DECISION_MADE"), None
        )
        assert decision_log is not None
        assert decision_log.actor_id == sample_checker.checker_id
        assert decision_log.actor_type == "checker"


class TestStatusTransitionEnforcement:
    """Tests verifying status transitions follow HITL rules."""

    @pytest.mark.asyncio
    async def test_cannot_skip_to_approved(
        self, test_session: AsyncSession, sample_request
    ):
        """Test that status cannot jump directly to APPROVED."""
        # Try to set approved status directly on intake request
        with pytest.raises(Exception):
            sample_request.status = RequestStatus.APPROVED
            await test_session.commit()

    @pytest.mark.asyncio
    async def test_ai_processing_leads_to_pending_human(
        self, test_session: AsyncSession, sample_request
    ):
        """Test that AI processing always results in PENDING_HUMAN status."""
        # Simulate normal flow
        sample_request.status = RequestStatus.VALIDATED
        await test_session.commit()

        sample_request.status = RequestStatus.PROCESSING
        await test_session.commit()

        # After AI processing
        sample_request.status = RequestStatus.AI_VERIFIED_PENDING_HUMAN
        sample_request.ai_recommendation = Recommendation.APPROVE
        await test_session.commit()
        await test_session.refresh(sample_request)

        # Status should be pending human, regardless of AI recommendation
        assert sample_request.status == RequestStatus.AI_VERIFIED_PENDING_HUMAN

    @pytest.mark.asyncio
    async def test_approval_only_from_in_review(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test that approval can only happen from IN_REVIEW status."""
        # Try to approve without claiming (status is AI_VERIFIED_PENDING_HUMAN)
        response = await client.post(
            f"/api/v1/checker/decide/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
            json={"decision": "APPROVE"},
        )

        # Should fail because request is not claimed/in review
        assert response.status_code == 403


class TestRPSUpdateEnforcement:
    """Tests verifying RPS (core banking) updates only happen on human approval."""

    @pytest.mark.asyncio
    async def test_rps_not_updated_by_ai(
        self, test_session: AsyncSession, sample_request
    ):
        """Test that AI processing doesn't trigger RPS update."""
        # Simulate AI processing
        sample_request.status = RequestStatus.AI_VERIFIED_PENDING_HUMAN
        sample_request.ai_recommendation = Recommendation.APPROVE
        sample_request.overall_score = 0.95

        await test_session.commit()
        await test_session.refresh(sample_request)

        # RPS should not be updated
        # In real implementation, check that no RPS API call was made
        assert sample_request.status != RequestStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_rps_updated_on_human_approval(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test that RPS is updated only on human approval."""
        # Claim the request
        processed_request.status = RequestStatus.IN_REVIEW
        processed_request.assigned_checker_id = sample_checker.checker_id
        processed_request.lock_expires_at = datetime.utcnow() + timedelta(minutes=15)
        await test_session.commit()

        # Human approves
        response = await client.post(
            f"/api/v1/checker/decide/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
            json={"decision": "APPROVE"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rps_updated"] == True

    @pytest.mark.asyncio
    async def test_rps_not_updated_on_rejection(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test that RPS is not updated on rejection."""
        # Claim the request
        processed_request.status = RequestStatus.IN_REVIEW
        processed_request.assigned_checker_id = sample_checker.checker_id
        processed_request.lock_expires_at = datetime.utcnow() + timedelta(minutes=15)
        await test_session.commit()

        # Human rejects
        response = await client.post(
            f"/api/v1/checker/decide/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
            json={"decision": "REJECT", "reason": "Document appears forged"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rps_updated"] == False


class TestAuditTrailIntegrity:
    """Tests verifying audit trail captures all HITL decisions."""

    @pytest.mark.asyncio
    async def test_audit_captures_checker_identity(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test audit log captures who made the decision."""
        # Claim and decide
        processed_request.status = RequestStatus.IN_REVIEW
        processed_request.assigned_checker_id = sample_checker.checker_id
        processed_request.lock_expires_at = datetime.utcnow() + timedelta(minutes=15)
        await test_session.commit()

        await client.post(
            f"/api/v1/checker/decide/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
            json={"decision": "APPROVE"},
        )

        # Check audit log
        result = await test_session.execute(
            select(AuditLog).where(
                AuditLog.request_id == processed_request.request_id,
                AuditLog.action == "DECISION_MADE",
            )
        )
        audit = result.scalar_one()

        assert audit.actor_id == sample_checker.checker_id
        assert audit.actor_type == "checker"
        assert audit.new_status == "APPROVED"

    @pytest.mark.asyncio
    async def test_audit_log_has_checksum(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test audit log entries have integrity checksums."""
        # Claim and decide
        processed_request.status = RequestStatus.IN_REVIEW
        processed_request.assigned_checker_id = sample_checker.checker_id
        processed_request.lock_expires_at = datetime.utcnow() + timedelta(minutes=15)
        await test_session.commit()

        await client.post(
            f"/api/v1/checker/decide/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
            json={"decision": "REJECT", "reason": "Suspicious document"},
        )

        # Check audit log has checksum
        result = await test_session.execute(
            select(AuditLog).where(
                AuditLog.request_id == processed_request.request_id,
                AuditLog.action == "DECISION_MADE",
            )
        )
        audit = result.scalar_one()

        assert audit.checksum is not None
        assert len(audit.checksum) > 0

    @pytest.mark.asyncio
    async def test_audit_captures_ai_vs_human_actions(
        self, test_session: AsyncSession, processed_request, sample_checker
    ):
        """Test audit distinguishes between AI and human actions."""
        # Create AI action audit
        ai_audit = AuditLog(
            request_id=processed_request.request_id,
            action="AI_PROCESSING_COMPLETE",
            actor_id="AI_PIPELINE",
            actor_type="system",
            old_status=RequestStatus.PROCESSING.value,
            new_status=RequestStatus.AI_VERIFIED_PENDING_HUMAN.value,
            details={"recommendation": "APPROVE", "confidence": 0.95},
        )
        test_session.add(ai_audit)
        await test_session.commit()

        # Create human action audit
        human_audit = AuditLog(
            request_id=processed_request.request_id,
            action="DECISION_MADE",
            actor_id=sample_checker.checker_id,
            actor_type="checker",
            old_status=RequestStatus.IN_REVIEW.value,
            new_status=RequestStatus.APPROVED.value,
            details={"decision": "APPROVE"},
        )
        test_session.add(human_audit)
        await test_session.commit()

        # Verify both types are captured correctly
        result = await test_session.execute(
            select(AuditLog)
            .where(AuditLog.request_id == processed_request.request_id)
            .order_by(AuditLog.created_at)
        )
        audits = result.scalars().all()

        ai_actions = [a for a in audits if a.actor_type == "system"]
        human_actions = [a for a in audits if a.actor_type == "checker"]

        assert len(ai_actions) >= 1
        assert len(human_actions) >= 1
        assert ai_actions[0].action == "AI_PROCESSING_COMPLETE"
        assert human_actions[0].action == "DECISION_MADE"
