"""
Tests for Checker API endpoints.
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.request import Request
from app.models.enums import RequestStatus, RiskTier, Recommendation, Decision


class TestGetQueue:
    """Tests for GET /api/v1/checker/queue endpoint."""

    @pytest.mark.asyncio
    async def test_get_queue_empty(self, client: AsyncClient):
        """Test getting empty queue."""
        response = await client.get("/api/v1/checker/queue")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_queue_with_items(
        self, client: AsyncClient, processed_request, queued_request
    ):
        """Test getting queue with items."""
        response = await client.get("/api/v1/checker/queue")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_get_queue_filter_by_risk_tier(
        self, client: AsyncClient, processed_request, queued_request
    ):
        """Test filtering queue by risk tier."""
        response = await client.get("/api/v1/checker/queue?risk_tier=LOW")

        assert response.status_code == 200
        data = response.json()
        assert all(item["risk_tier"] == "LOW" for item in data["items"])

    @pytest.mark.asyncio
    async def test_get_queue_filter_by_recommendation(
        self, client: AsyncClient, processed_request, queued_request
    ):
        """Test filtering queue by AI recommendation."""
        response = await client.get("/api/v1/checker/queue?ai_recommendation=APPROVE")

        assert response.status_code == 200
        data = response.json()
        assert all(item["ai_recommendation"] == "APPROVE" for item in data["items"])

    @pytest.mark.asyncio
    async def test_get_queue_excludes_claimed(
        self, client: AsyncClient, test_session: AsyncSession, processed_request
    ):
        """Test that claimed requests are excluded from queue."""
        # Claim the request
        processed_request.status = RequestStatus.IN_REVIEW
        processed_request.assigned_checker_id = "CHK-001"
        await test_session.commit()

        response = await client.get("/api/v1/checker/queue")

        assert response.status_code == 200
        data = response.json()
        assert all(
            item["request_id"] != processed_request.request_id
            for item in data["items"]
        )

    @pytest.mark.asyncio
    async def test_get_queue_pagination(
        self, client: AsyncClient, processed_request, queued_request
    ):
        """Test queue pagination."""
        response = await client.get("/api/v1/checker/queue?page=1&limit=1")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["limit"] == 1


class TestClaimRequest:
    """Tests for POST /api/v1/checker/claim/{request_id} endpoint."""

    @pytest.mark.asyncio
    async def test_claim_request_success(
        self, client: AsyncClient, processed_request, sample_checker
    ):
        """Test successful request claim."""
        response = await client.post(
            f"/api/v1/checker/claim/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == processed_request.request_id
        assert data["assigned_to"] == sample_checker.checker_id
        assert "lock_expires_at" in data

    @pytest.mark.asyncio
    async def test_claim_request_not_found(self, client: AsyncClient, sample_checker):
        """Test claiming non-existent request."""
        response = await client.post(
            "/api/v1/checker/claim/non-existent-id",
            params={"checker_id": sample_checker.checker_id},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_claim_request_already_claimed(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test claiming already claimed request."""
        # First claim
        processed_request.status = RequestStatus.IN_REVIEW
        processed_request.assigned_checker_id = "OTHER-CHECKER"
        processed_request.lock_expires_at = datetime.utcnow() + timedelta(minutes=15)
        await test_session.commit()

        response = await client.post(
            f"/api/v1/checker/claim/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
        )

        assert response.status_code == 409
        assert "already claimed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_claim_request_invalid_status(
        self, client: AsyncClient, sample_request, sample_checker
    ):
        """Test claiming request with invalid status."""
        response = await client.post(
            f"/api/v1/checker/claim/{sample_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_claim_request_expired_lock_reclaim(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test reclaiming request with expired lock."""
        # Set expired lock
        processed_request.status = RequestStatus.IN_REVIEW
        processed_request.assigned_checker_id = "OTHER-CHECKER"
        processed_request.lock_expires_at = datetime.utcnow() - timedelta(minutes=1)
        await test_session.commit()

        response = await client.post(
            f"/api/v1/checker/claim/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["assigned_to"] == sample_checker.checker_id


class TestGetReviewData:
    """Tests for GET /api/v1/checker/review/{request_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_review_data_success(
        self, client: AsyncClient, processed_request
    ):
        """Test getting review data for a request."""
        response = await client.get(
            f"/api/v1/checker/review/{processed_request.request_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == processed_request.request_id
        assert data["customer_id"] == processed_request.customer_id
        assert data["risk_tier"] == "LOW"
        assert data["ai_recommendation"] == "APPROVE"
        assert "ai_summary" in data
        assert "field_scores" in data

    @pytest.mark.asyncio
    async def test_get_review_data_not_found(self, client: AsyncClient):
        """Test getting review data for non-existent request."""
        response = await client.get("/api/v1/checker/review/non-existent-id")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_review_data_includes_all_fields(
        self, client: AsyncClient, processed_request
    ):
        """Test that review data includes all necessary fields."""
        response = await client.get(
            f"/api/v1/checker/review/{processed_request.request_id}"
        )

        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "request_id",
            "customer_id",
            "change_type",
            "document_type",
            "requested_old_value",
            "requested_new_value",
            "extracted_old_value",
            "extracted_new_value",
            "field_scores",
            "ocr_confidence",
            "extraction_confidence",
            "doc_authenticity_score",
            "overall_score",
            "risk_tier",
            "flags",
            "ai_recommendation",
            "ai_summary",
            "created_at",
        ]

        for field in required_fields:
            assert field in data


class TestSubmitDecision:
    """Tests for POST /api/v1/checker/decide/{request_id} endpoint."""

    @pytest.mark.asyncio
    async def test_submit_decision_approve(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test approving a request."""
        # Claim first
        processed_request.status = RequestStatus.IN_REVIEW
        processed_request.assigned_checker_id = sample_checker.checker_id
        processed_request.lock_expires_at = datetime.utcnow() + timedelta(minutes=15)
        await test_session.commit()

        response = await client.post(
            f"/api/v1/checker/decide/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
            json={"decision": "APPROVE"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "APPROVE"
        assert data["new_status"] == "APPROVED"
        assert data["rps_updated"] == True

    @pytest.mark.asyncio
    async def test_submit_decision_reject_requires_reason(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test that rejecting requires a reason."""
        # Claim first
        processed_request.status = RequestStatus.IN_REVIEW
        processed_request.assigned_checker_id = sample_checker.checker_id
        processed_request.lock_expires_at = datetime.utcnow() + timedelta(minutes=15)
        await test_session.commit()

        response = await client.post(
            f"/api/v1/checker/decide/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
            json={"decision": "REJECT"},
        )

        assert response.status_code == 400
        assert "reason" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_submit_decision_reject_with_reason(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test rejecting with a reason."""
        # Claim first
        processed_request.status = RequestStatus.IN_REVIEW
        processed_request.assigned_checker_id = sample_checker.checker_id
        processed_request.lock_expires_at = datetime.utcnow() + timedelta(minutes=15)
        await test_session.commit()

        response = await client.post(
            f"/api/v1/checker/decide/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
            json={"decision": "REJECT", "reason": "Document appears tampered"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "REJECT"
        assert data["new_status"] == "REJECTED"

    @pytest.mark.asyncio
    async def test_submit_decision_more_info(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test requesting more information."""
        # Claim first
        processed_request.status = RequestStatus.IN_REVIEW
        processed_request.assigned_checker_id = sample_checker.checker_id
        processed_request.lock_expires_at = datetime.utcnow() + timedelta(minutes=15)
        await test_session.commit()

        response = await client.post(
            f"/api/v1/checker/decide/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
            json={"decision": "MORE_INFO", "reason": "Need clearer document image"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "MORE_INFO"
        assert data["new_status"] == "PENDING_INFO"

    @pytest.mark.asyncio
    async def test_submit_decision_escalate(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test escalating a request."""
        # Claim first
        processed_request.status = RequestStatus.IN_REVIEW
        processed_request.assigned_checker_id = sample_checker.checker_id
        processed_request.lock_expires_at = datetime.utcnow() + timedelta(minutes=15)
        await test_session.commit()

        response = await client.post(
            f"/api/v1/checker/decide/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
            json={"decision": "ESCALATE", "reason": "Potential fraud detected"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "ESCALATE"
        assert data["new_status"] == "ESCALATED"

    @pytest.mark.asyncio
    async def test_submit_decision_not_claimed(
        self, client: AsyncClient, processed_request, sample_checker
    ):
        """Test submitting decision on unclaimed request."""
        response = await client.post(
            f"/api/v1/checker/decide/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
            json={"decision": "APPROVE"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_submit_decision_wrong_checker(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test submitting decision by different checker."""
        # Claim by different checker
        processed_request.status = RequestStatus.IN_REVIEW
        processed_request.assigned_checker_id = "OTHER-CHECKER"
        processed_request.lock_expires_at = datetime.utcnow() + timedelta(minutes=15)
        await test_session.commit()

        response = await client.post(
            f"/api/v1/checker/decide/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
            json={"decision": "APPROVE"},
        )

        assert response.status_code == 403


class TestReleaseRequest:
    """Tests for POST /api/v1/checker/release/{request_id} endpoint."""

    @pytest.mark.asyncio
    async def test_release_request_success(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test releasing a claimed request."""
        # Claim first
        processed_request.status = RequestStatus.IN_REVIEW
        processed_request.assigned_checker_id = sample_checker.checker_id
        processed_request.lock_expires_at = datetime.utcnow() + timedelta(minutes=15)
        await test_session.commit()

        response = await client.post(
            f"/api/v1/checker/release/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
        )

        assert response.status_code == 200
        assert "released" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_release_request_not_claimed(
        self, client: AsyncClient, processed_request, sample_checker
    ):
        """Test releasing unclaimed request."""
        response = await client.post(
            f"/api/v1/checker/release/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_release_request_wrong_checker(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        processed_request,
        sample_checker,
    ):
        """Test releasing by different checker."""
        # Claim by different checker
        processed_request.status = RequestStatus.IN_REVIEW
        processed_request.assigned_checker_id = "OTHER-CHECKER"
        processed_request.lock_expires_at = datetime.utcnow() + timedelta(minutes=15)
        await test_session.commit()

        response = await client.post(
            f"/api/v1/checker/release/{processed_request.request_id}",
            params={"checker_id": sample_checker.checker_id},
        )

        assert response.status_code == 403
