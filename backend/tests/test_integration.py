"""
Integration tests for end-to-end request flows.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.models.request import Request
from app.models.enums import RequestStatus, RiskTier, Recommendation


class TestCompleteRequestFlow:
    """Integration tests for complete request lifecycle."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_approval_flow(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        sample_customer,
        sample_checker,
        sample_pdf_bytes,
        mock_celery_task,
    ):
        """Test complete flow: create -> upload -> process -> review -> approve."""
        # 1. Create request
        create_response = await client.post(
            "/api/v1/requests",
            json={
                "customer_id": sample_customer.customer_id,
                "change_type": "LEGAL_NAME",
                "document_type": "MARRIAGE_CERTIFICATE",
                "current_value": "John Doe",
                "new_value": "John Smith",
            },
        )
        assert create_response.status_code == 201
        request_id = create_response.json()["request_id"]

        # 2. Upload document
        files = {"file": ("test.pdf", sample_pdf_bytes, "application/pdf")}
        upload_response = await client.post(
            f"/api/v1/requests/{request_id}/upload",
            files=files,
        )
        assert upload_response.status_code == 200

        # 3. Simulate AI processing completion
        from sqlalchemy import select

        result = await test_session.execute(
            select(Request).where(Request.request_id == request_id)
        )
        request = result.scalar_one()
        request.status = RequestStatus.AI_VERIFIED_PENDING_HUMAN
        request.ocr_confidence = 0.95
        request.extraction_confidence = 0.92
        request.overall_score = 0.91
        request.risk_tier = RiskTier.LOW
        request.ai_recommendation = Recommendation.APPROVE
        request.ai_summary = "Document verified successfully."
        await test_session.commit()

        # 4. Verify request appears in queue
        queue_response = await client.get("/api/v1/checker/queue")
        assert queue_response.status_code == 200
        queue_items = queue_response.json()["items"]
        assert any(item["request_id"] == request_id for item in queue_items)

        # 5. Claim the request
        claim_response = await client.post(
            f"/api/v1/checker/claim/{request_id}",
            params={"checker_id": sample_checker.checker_id},
        )
        assert claim_response.status_code == 200

        # 6. Get review data
        review_response = await client.get(f"/api/v1/checker/review/{request_id}")
        assert review_response.status_code == 200
        assert review_response.json()["ai_recommendation"] == "APPROVE"

        # 7. Submit approval decision
        decision_response = await client.post(
            f"/api/v1/checker/decide/{request_id}",
            params={"checker_id": sample_checker.checker_id},
            json={"decision": "APPROVE"},
        )
        assert decision_response.status_code == 200
        assert decision_response.json()["new_status"] == "APPROVED"
        assert decision_response.json()["rps_updated"] == True

        # 8. Verify final status
        final_response = await client.get(f"/api/v1/requests/{request_id}")
        assert final_response.status_code == 200
        assert final_response.json()["status"] == "APPROVED"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_rejection_flow(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        sample_customer,
        sample_checker,
        sample_pdf_bytes,
        mock_celery_task,
    ):
        """Test complete flow with rejection."""
        # 1. Create request
        create_response = await client.post(
            "/api/v1/requests",
            json={
                "customer_id": sample_customer.customer_id,
                "change_type": "LEGAL_NAME",
                "document_type": "MARRIAGE_CERTIFICATE",
                "current_value": "John Doe",
                "new_value": "John Smith",
            },
        )
        request_id = create_response.json()["request_id"]

        # 2. Upload and simulate processing
        files = {"file": ("test.pdf", sample_pdf_bytes, "application/pdf")}
        await client.post(f"/api/v1/requests/{request_id}/upload", files=files)

        from sqlalchemy import select

        result = await test_session.execute(
            select(Request).where(Request.request_id == request_id)
        )
        request = result.scalar_one()
        request.status = RequestStatus.AI_VERIFIED_PENDING_HUMAN
        request.overall_score = 0.55
        request.risk_tier = RiskTier.HIGH
        request.ai_recommendation = Recommendation.REJECT
        request.flags = ["potential_forgery", "name_mismatch"]
        await test_session.commit()

        # 3. Claim and reject
        await client.post(
            f"/api/v1/checker/claim/{request_id}",
            params={"checker_id": sample_checker.checker_id},
        )

        decision_response = await client.post(
            f"/api/v1/checker/decide/{request_id}",
            params={"checker_id": sample_checker.checker_id},
            json={"decision": "REJECT", "reason": "Document appears tampered"},
        )

        assert decision_response.status_code == 200
        assert decision_response.json()["new_status"] == "REJECTED"
        assert decision_response.json()["rps_updated"] == False

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_escalation_flow(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        sample_customer,
        sample_checker,
        sample_pdf_bytes,
        mock_celery_task,
    ):
        """Test escalation flow for suspicious documents."""
        # Create and process request
        create_response = await client.post(
            "/api/v1/requests",
            json={
                "customer_id": sample_customer.customer_id,
                "change_type": "LEGAL_NAME",
                "document_type": "MARRIAGE_CERTIFICATE",
                "current_value": "John Doe",
                "new_value": "John Smith",
            },
        )
        request_id = create_response.json()["request_id"]

        files = {"file": ("test.pdf", sample_pdf_bytes, "application/pdf")}
        await client.post(f"/api/v1/requests/{request_id}/upload", files=files)

        from sqlalchemy import select

        result = await test_session.execute(
            select(Request).where(Request.request_id == request_id)
        )
        request = result.scalar_one()
        request.status = RequestStatus.AI_VERIFIED_PENDING_HUMAN
        request.overall_score = 0.70
        request.risk_tier = RiskTier.MEDIUM
        request.ai_recommendation = Recommendation.MANUAL_REVIEW
        await test_session.commit()

        # Claim and escalate
        await client.post(
            f"/api/v1/checker/claim/{request_id}",
            params={"checker_id": sample_checker.checker_id},
        )

        decision_response = await client.post(
            f"/api/v1/checker/decide/{request_id}",
            params={"checker_id": sample_checker.checker_id},
            json={"decision": "ESCALATE", "reason": "Needs senior review"},
        )

        assert decision_response.status_code == 200
        assert decision_response.json()["new_status"] == "ESCALATED"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_more_info_flow(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        sample_customer,
        sample_checker,
        sample_pdf_bytes,
        mock_celery_task,
    ):
        """Test requesting more information flow."""
        # Create and process request
        create_response = await client.post(
            "/api/v1/requests",
            json={
                "customer_id": sample_customer.customer_id,
                "change_type": "LEGAL_NAME",
                "document_type": "MARRIAGE_CERTIFICATE",
                "current_value": "John Doe",
                "new_value": "John Smith",
            },
        )
        request_id = create_response.json()["request_id"]

        files = {"file": ("test.pdf", sample_pdf_bytes, "application/pdf")}
        await client.post(f"/api/v1/requests/{request_id}/upload", files=files)

        from sqlalchemy import select

        result = await test_session.execute(
            select(Request).where(Request.request_id == request_id)
        )
        request = result.scalar_one()
        request.status = RequestStatus.AI_VERIFIED_PENDING_HUMAN
        request.ocr_confidence = 0.60
        request.ai_recommendation = Recommendation.MANUAL_REVIEW
        await test_session.commit()

        # Claim and request more info
        await client.post(
            f"/api/v1/checker/claim/{request_id}",
            params={"checker_id": sample_checker.checker_id},
        )

        decision_response = await client.post(
            f"/api/v1/checker/decide/{request_id}",
            params={"checker_id": sample_checker.checker_id},
            json={"decision": "MORE_INFO", "reason": "Document is blurry"},
        )

        assert decision_response.status_code == 200
        assert decision_response.json()["new_status"] == "PENDING_INFO"


class TestConcurrencyScenarios:
    """Tests for concurrent access scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_claim_attempts(
        self, client: AsyncClient, processed_request, sample_checker
    ):
        """Test that only one checker can claim a request."""
        # First claim should succeed
        first_response = await client.post(
            f"/api/v1/checker/claim/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
        )
        assert first_response.status_code == 200

        # Second claim should fail
        second_response = await client.post(
            f"/api/v1/checker/claim/{processed_request.request_id}",
            params={"checker_id": "OTHER-CHECKER"},
        )
        assert second_response.status_code == 409

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_lock_expiry_and_reclaim(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test that expired locks allow reclaiming."""
        # Set expired lock
        processed_request.status = RequestStatus.IN_REVIEW
        processed_request.assigned_checker_id = "EXPIRED-CHECKER"
        processed_request.lock_expires_at = datetime.utcnow() - timedelta(minutes=5)
        await test_session.commit()

        # New claim should succeed
        response = await client.post(
            f"/api/v1/checker/claim/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
        )
        assert response.status_code == 200
        assert response.json()["assigned_to"] == sample_checker.checker_id


class TestErrorRecovery:
    """Tests for error handling and recovery."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_release_and_reclaim(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test releasing and reclaiming a request."""
        # Claim
        claim_response = await client.post(
            f"/api/v1/checker/claim/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
        )
        assert claim_response.status_code == 200

        # Release
        release_response = await client.post(
            f"/api/v1/checker/release/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
        )
        assert release_response.status_code == 200

        # Reclaim by different checker
        reclaim_response = await client.post(
            f"/api/v1/checker/claim/{processed_request.request_id}",
            params={"checker_id": "ANOTHER-CHECKER"},
        )
        assert reclaim_response.status_code == 200
        assert reclaim_response.json()["assigned_to"] == "ANOTHER-CHECKER"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_status_transitions_blocked(
        self, client: AsyncClient, sample_request, sample_checker
    ):
        """Test that invalid status transitions are blocked."""
        # Try to claim a request that's not ready for review
        response = await client.post(
            f"/api/v1/checker/claim/{sample_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
        )
        assert response.status_code == 400
