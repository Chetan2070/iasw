"""
Tests for Request API endpoints.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock

from app.models.request import Request
from app.models.enums import RequestStatus, ChangeType, DocumentType


class TestCreateRequest:
    """Tests for POST /api/v1/requests endpoint."""

    @pytest.mark.asyncio
    async def test_create_request_success(
        self, client: AsyncClient, sample_customer, mock_celery_task
    ):
        """Test successful request creation."""
        payload = {
            "customer_id": sample_customer.customer_id,
            "change_type": "LEGAL_NAME",
            "document_type": "MARRIAGE_CERTIFICATE",
            "current_value": "John Doe",
            "new_value": "John Smith",
        }

        response = await client.post("/api/v1/requests", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert "request_id" in data
        assert data["status"] == "INTAKE_RECEIVED"
        assert data["message"] == "Request created successfully"

    @pytest.mark.asyncio
    async def test_create_request_invalid_change_type(self, client: AsyncClient):
        """Test request creation with invalid change type."""
        payload = {
            "customer_id": "CUST-001",
            "change_type": "INVALID_TYPE",
            "document_type": "MARRIAGE_CERTIFICATE",
            "current_value": "John Doe",
            "new_value": "John Smith",
        }

        response = await client.post("/api/v1/requests", json=payload)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_request_invalid_document_for_change_type(
        self, client: AsyncClient, sample_customer
    ):
        """Test request creation with document type not allowed for change type."""
        payload = {
            "customer_id": sample_customer.customer_id,
            "change_type": "LEGAL_NAME",
            "document_type": "UTILITY_BILL",  # Not valid for LEGAL_NAME
            "current_value": "John Doe",
            "new_value": "John Smith",
        }

        response = await client.post("/api/v1/requests", json=payload)

        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_request_missing_required_fields(self, client: AsyncClient):
        """Test request creation with missing required fields."""
        payload = {
            "customer_id": "CUST-001",
            # Missing other required fields
        }

        response = await client.post("/api/v1/requests", json=payload)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_request_empty_values(self, client: AsyncClient, sample_customer):
        """Test request creation with empty values."""
        payload = {
            "customer_id": sample_customer.customer_id,
            "change_type": "LEGAL_NAME",
            "document_type": "MARRIAGE_CERTIFICATE",
            "current_value": "",
            "new_value": "",
        }

        response = await client.post("/api/v1/requests", json=payload)

        assert response.status_code == 422


class TestUploadDocument:
    """Tests for POST /api/v1/requests/{request_id}/upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_document_success(
        self, client: AsyncClient, sample_request, sample_pdf_bytes, mock_celery_task
    ):
        """Test successful document upload."""
        files = {"file": ("test_document.pdf", sample_pdf_bytes, "application/pdf")}

        response = await client.post(
            f"/api/v1/requests/{sample_request.request_id}/upload",
            files=files,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == sample_request.request_id
        assert "document_id" in data
        mock_celery_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_document_invalid_request_id(
        self, client: AsyncClient, sample_pdf_bytes
    ):
        """Test upload to non-existent request."""
        files = {"file": ("test_document.pdf", sample_pdf_bytes, "application/pdf")}

        response = await client.post(
            "/api/v1/requests/non-existent-id/upload",
            files=files,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_document_invalid_file_type(
        self, client: AsyncClient, sample_request
    ):
        """Test upload with invalid file type."""
        files = {"file": ("test.exe", b"fake executable content", "application/x-msdownload")}

        response = await client.post(
            f"/api/v1/requests/{sample_request.request_id}/upload",
            files=files,
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_document_too_large(
        self, client: AsyncClient, sample_request
    ):
        """Test upload with file exceeding size limit."""
        # Create a file larger than 10MB
        large_content = b"x" * (11 * 1024 * 1024)
        files = {"file": ("large_file.pdf", large_content, "application/pdf")}

        response = await client.post(
            f"/api/v1/requests/{sample_request.request_id}/upload",
            files=files,
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_document_already_processed(
        self, client: AsyncClient, processed_request, sample_pdf_bytes
    ):
        """Test upload to already processed request."""
        files = {"file": ("test_document.pdf", sample_pdf_bytes, "application/pdf")}

        response = await client.post(
            f"/api/v1/requests/{processed_request.request_id}/upload",
            files=files,
        )

        assert response.status_code == 400


class TestListRequests:
    """Tests for GET /api/v1/requests endpoint."""

    @pytest.mark.asyncio
    async def test_list_requests_empty(self, client: AsyncClient):
        """Test listing requests when none exist."""
        response = await client.get("/api/v1/requests")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_requests_with_data(
        self, client: AsyncClient, sample_request, processed_request
    ):
        """Test listing requests with existing data."""
        response = await client.get("/api/v1/requests")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_list_requests_filter_by_customer(
        self, client: AsyncClient, sample_request
    ):
        """Test filtering requests by customer ID."""
        response = await client.get(
            f"/api/v1/requests?customer_id={sample_request.customer_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert all(
            item["customer_id"] == sample_request.customer_id
            for item in data["items"]
        )

    @pytest.mark.asyncio
    async def test_list_requests_filter_by_status(
        self, client: AsyncClient, sample_request, processed_request
    ):
        """Test filtering requests by status."""
        response = await client.get("/api/v1/requests?status=INTAKE_RECEIVED")

        assert response.status_code == 200
        data = response.json()
        assert all(item["status"] == "INTAKE_RECEIVED" for item in data["items"])

    @pytest.mark.asyncio
    async def test_list_requests_filter_by_change_type(
        self, client: AsyncClient, sample_request
    ):
        """Test filtering requests by change type."""
        response = await client.get("/api/v1/requests?change_type=LEGAL_NAME")

        assert response.status_code == 200
        data = response.json()
        assert all(item["change_type"] == "LEGAL_NAME" for item in data["items"])

    @pytest.mark.asyncio
    async def test_list_requests_pagination(
        self, client: AsyncClient, sample_request, processed_request, queued_request
    ):
        """Test request list pagination."""
        response = await client.get("/api/v1/requests?page=1&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["pages"] >= 1


class TestGetRequest:
    """Tests for GET /api/v1/requests/{request_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_request_success(self, client: AsyncClient, sample_request):
        """Test getting a specific request."""
        response = await client.get(f"/api/v1/requests/{sample_request.request_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == sample_request.request_id
        assert data["customer_id"] == sample_request.customer_id
        assert data["change_type"] == sample_request.change_type.value

    @pytest.mark.asyncio
    async def test_get_request_not_found(self, client: AsyncClient):
        """Test getting a non-existent request."""
        response = await client.get("/api/v1/requests/non-existent-id")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_request_includes_ai_fields(
        self, client: AsyncClient, processed_request
    ):
        """Test that processed request includes AI fields."""
        response = await client.get(f"/api/v1/requests/{processed_request.request_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["risk_tier"] == "LOW"
        assert data["ai_recommendation"] == "APPROVE"
        assert data["overall_confidence"] is not None
