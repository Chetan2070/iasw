"""
Pytest configuration and fixtures for IASW backend tests.
"""

import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.db.session import get_db
from app.models.request import Base, Request
from app.models.customer import Customer, Checker
from app.models.audit import AuditLog
from app.models.enums import (
    ChangeType,
    DocumentType,
    RequestStatus,
    RiskTier,
    Recommendation,
)


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_engine, test_session) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database override."""
    app = create_app()

    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_customer(test_session: AsyncSession) -> Customer:
    """Create a sample customer for testing."""
    customer = Customer(
        customer_id="CUST-TEST-001",
        full_name="John Doe",
        date_of_birth="1990-01-15",
        address="123 Test Street, Test City",
        email="john.doe@test.com",
        phone="+1234567890",
    )
    test_session.add(customer)
    await test_session.commit()
    await test_session.refresh(customer)
    return customer


@pytest_asyncio.fixture
async def sample_checker(test_session: AsyncSession) -> Checker:
    """Create a sample checker for testing."""
    checker = Checker(
        checker_id="CHK-TEST-001",
        name="Test Checker",
        email="checker@test.com",
        is_active=True,
    )
    test_session.add(checker)
    await test_session.commit()
    await test_session.refresh(checker)
    return checker


@pytest_asyncio.fixture
async def sample_request(test_session: AsyncSession, sample_customer: Customer) -> Request:
    """Create a sample pending request for testing."""
    request = Request(
        request_id=str(uuid.uuid4()),
        customer_id=sample_customer.customer_id,
        change_type=ChangeType.LEGAL_NAME,
        document_type=DocumentType.MARRIAGE_CERTIFICATE,
        requested_old_value="John Doe",
        requested_new_value="John Smith",
        status=RequestStatus.INTAKE_RECEIVED,
    )
    test_session.add(request)
    await test_session.commit()
    await test_session.refresh(request)
    return request


@pytest_asyncio.fixture
async def processed_request(test_session: AsyncSession, sample_customer: Customer) -> Request:
    """Create a processed request ready for review."""
    request = Request(
        request_id=str(uuid.uuid4()),
        customer_id=sample_customer.customer_id,
        change_type=ChangeType.LEGAL_NAME,
        document_type=DocumentType.MARRIAGE_CERTIFICATE,
        requested_old_value="John Doe",
        requested_new_value="John Smith",
        status=RequestStatus.AI_VERIFIED_PENDING_HUMAN,
        document_path="/tmp/test_doc.pdf",
        ocr_confidence=0.95,
        extraction_confidence=0.92,
        doc_authenticity_score=0.88,
        overall_score=0.91,
        risk_tier=RiskTier.LOW,
        ai_recommendation=Recommendation.APPROVE,
        ai_summary="Document verified successfully. High confidence match.",
        extracted_old_value="John Doe",
        extracted_new_value="John Smith",
    )
    test_session.add(request)
    await test_session.commit()
    await test_session.refresh(request)
    return request


@pytest_asyncio.fixture
async def queued_request(test_session: AsyncSession, sample_customer: Customer) -> Request:
    """Create a request in the queue."""
    request = Request(
        request_id=str(uuid.uuid4()),
        customer_id=sample_customer.customer_id,
        change_type=ChangeType.ADDRESS,
        document_type=DocumentType.UTILITY_BILL,
        requested_old_value="123 Old Street",
        requested_new_value="456 New Avenue",
        status=RequestStatus.AI_VERIFIED_PENDING_HUMAN,
        document_path="/tmp/test_doc.pdf",
        ocr_confidence=0.85,
        extraction_confidence=0.80,
        doc_authenticity_score=0.75,
        overall_score=0.78,
        risk_tier=RiskTier.MEDIUM,
        ai_recommendation=Recommendation.MANUAL_REVIEW,
        ai_summary="Document requires manual verification due to medium confidence.",
        flags=["low_ocr_confidence", "address_format_mismatch"],
    )
    test_session.add(request)
    await test_session.commit()
    await test_session.refresh(request)
    return request


@pytest.fixture
def mock_celery_task():
    """Mock Celery task for testing."""
    with patch("app.workers.tasks.process_document.delay") as mock:
        mock.return_value = MagicMock(id="test-task-id")
        yield mock


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for LLM calls."""
    with patch("anthropic.Anthropic") as mock:
        mock_instance = MagicMock()
        mock_instance.messages.create.return_value = MagicMock(
            content=[MagicMock(text='{"classification": "MARRIAGE_CERTIFICATE", "confidence": 0.95}')]
        )
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_image_bytes() -> bytes:
    """Create sample image bytes for testing."""
    # Minimal valid PNG (1x1 transparent pixel)
    return bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
        0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
        0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
        0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
        0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
        0x42, 0x60, 0x82
    ])


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Create minimal sample PDF bytes for testing."""
    pdf_content = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer << /Size 4 /Root 1 0 R >>
startxref
196
%%EOF"""
    return pdf_content
