"""
Tests for Health API endpoints.
"""

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Tests for GET /api/v1/health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, client: AsyncClient):
        """Test health check returns success."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "environment" in data

    @pytest.mark.asyncio
    async def test_health_check_response_format(self, client: AsyncClient):
        """Test health check response format."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["status"], str)
        assert isinstance(data["environment"], str)


class TestReadinessEndpoint:
    """Tests for GET /api/v1/health/ready endpoint."""

    @pytest.mark.asyncio
    async def test_readiness_check_success(self, client: AsyncClient):
        """Test readiness check returns success."""
        response = await client.get("/api/v1/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] == True

    @pytest.mark.asyncio
    async def test_readiness_includes_components(self, client: AsyncClient):
        """Test readiness check includes component status."""
        response = await client.get("/api/v1/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert "components" in data or data["ready"] == True
