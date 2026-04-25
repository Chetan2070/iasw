"""
Tests for LangGraph document processing pipeline.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import os
import tempfile

from app.agents.state import ProcessingState, create_initial_state
from app.agents.graph import DocumentProcessingPipeline
from app.agents.nodes.validation import validation_node, route_after_validation
from app.agents.nodes.ocr import ocr_node
from app.agents.nodes.classifier import classifier_node
from app.agents.nodes.extractor import extractor_node
from app.agents.nodes.forgery import forgery_node
from app.agents.nodes.scorer import scorer_node
from app.agents.nodes.summary import summary_node
from app.models.enums import ChangeType, DocumentType


class TestValidationNode:
    """Tests for validation_node function."""

    @pytest.mark.asyncio
    async def test_validation_success(self, tmp_path):
        """Test successful validation with all required fields."""
        doc_file = tmp_path / "test_doc.pdf"
        doc_file.write_bytes(b"fake pdf content")

        state = {
            "request_id": "test-123",
            "customer_id": "CUST-001",
            "document_path": str(doc_file),
        }

        result = await validation_node(state)

        assert result["validation_passed"] is True
        assert result["validation_errors"] == []
        assert result["current_step"] == "validation"

    @pytest.mark.asyncio
    async def test_validation_missing_request_id(self, tmp_path):
        """Test validation fails without request_id."""
        doc_file = tmp_path / "test_doc.pdf"
        doc_file.write_bytes(b"fake pdf content")

        state = {
            "request_id": "",
            "customer_id": "CUST-001",
            "document_path": str(doc_file),
        }

        result = await validation_node(state)

        assert result["validation_passed"] is False
        assert "Missing request_id" in result["validation_errors"]

    @pytest.mark.asyncio
    async def test_validation_missing_document_path(self):
        """Test validation fails without document_path."""
        state = {
            "request_id": "test-123",
            "customer_id": "CUST-001",
            "document_path": "",
        }

        result = await validation_node(state)

        assert result["validation_passed"] is False
        assert "Missing document_path" in result["validation_errors"]

    @pytest.mark.asyncio
    async def test_validation_document_not_found(self):
        """Test validation fails when document file doesn't exist."""
        state = {
            "request_id": "test-123",
            "customer_id": "CUST-001",
            "document_path": "/nonexistent/path/doc.pdf",
        }

        result = await validation_node(state)

        assert result["validation_passed"] is False
        assert any("not found" in e for e in result["validation_errors"])

    @pytest.mark.asyncio
    async def test_validation_empty_document(self, tmp_path):
        """Test validation fails for empty document file."""
        doc_file = tmp_path / "empty.pdf"
        doc_file.write_bytes(b"")

        state = {
            "request_id": "test-123",
            "customer_id": "CUST-001",
            "document_path": str(doc_file),
        }

        result = await validation_node(state)

        assert result["validation_passed"] is False
        assert any("empty" in e for e in result["validation_errors"])


class TestValidationRouting:
    """Tests for validation routing function."""

    def test_route_after_validation_continue(self):
        """Test routing continues when validation passes."""
        state = {"validation_passed": True}
        assert route_after_validation(state) == "continue"

    def test_route_after_validation_fail(self):
        """Test routing fails when validation fails."""
        state = {"validation_passed": False}
        assert route_after_validation(state) == "fail"

    def test_route_after_validation_missing(self):
        """Test routing fails when validation_passed is missing."""
        state = {}
        assert route_after_validation(state) == "fail"


class TestOCRNode:
    """Tests for ocr_node function."""

    @pytest.mark.asyncio
    async def test_ocr_node_with_mock(self, tmp_path, sample_image_bytes):
        """Test OCR node with mocked Tesseract."""
        doc_file = tmp_path / "test.png"
        doc_file.write_bytes(sample_image_bytes)

        state = {
            "request_id": "test-123",
            "document_path": str(doc_file),
            "flags": [],
        }

        with patch("pytesseract.image_to_string") as mock_to_string, \
             patch("pytesseract.image_to_data") as mock_to_data:
            mock_to_string.return_value = "Extracted document text"
            mock_to_data.return_value = {"conf": [95, 92, 88]}

            result = await ocr_node(state)

        assert "ocr_text" in result
        assert "ocr_confidence" in result
        assert result["current_step"] == "ocr"


class TestScorerNode:
    """Tests for scorer_node function."""

    @pytest.mark.asyncio
    async def test_scorer_high_confidence(self):
        """Test scoring for high confidence case."""
        state = {
            "request_id": "test-123",
            "extracted_old_value": "John Doe",
            "extracted_new_value": "John Smith",
            "requested_old_value": "John Doe",
            "requested_new_value": "John Smith",
            "forgery_score": 0.95,
            "ocr_confidence": 0.95,
            "extraction_confidence": 0.93,
            "flags": [],
        }

        result = await scorer_node(state)

        assert result["overall_score"] >= 0.9
        assert result["risk_tier"] == "LOW"

    @pytest.mark.asyncio
    async def test_scorer_low_confidence(self):
        """Test scoring for low confidence case."""
        state = {
            "request_id": "test-123",
            "extracted_old_value": "Jane Doe",
            "extracted_new_value": "Jane Smith",
            "requested_old_value": "John Doe",
            "requested_new_value": "John Smith",
            "forgery_score": 0.50,
            "ocr_confidence": 0.55,
            "extraction_confidence": 0.50,
            "flags": [],
        }

        result = await scorer_node(state)

        assert result["overall_score"] < 0.8
        assert result["risk_tier"] in ["MEDIUM", "HIGH"]

    @pytest.mark.asyncio
    async def test_scorer_adds_name_mismatch_flags(self):
        """Test that scorer adds appropriate flags for name mismatches."""
        state = {
            "request_id": "test-123",
            "extracted_old_value": "Wrong Name",
            "extracted_new_value": "Also Wrong",
            "requested_old_value": "John Doe",
            "requested_new_value": "John Smith",
            "forgery_score": 0.95,
            "ocr_confidence": 0.95,
            "extraction_confidence": 0.95,
            "flags": [],
        }

        result = await scorer_node(state)

        assert any("MISMATCH" in f or "FUZZY" in f for f in result["flags"])


class TestCreateInitialState:
    """Tests for create_initial_state function."""

    def test_create_initial_state_basic(self):
        """Test creating initial state with basic fields."""
        state = create_initial_state(
            request_id="test-123",
            customer_id="CUST-001",
            change_type="LEGAL_NAME",
            document_type="MARRIAGE_CERTIFICATE",
            document_path="/tmp/doc.pdf",
            requested_old_value="John Doe",
            requested_new_value="John Smith",
        )

        assert state["request_id"] == "test-123"
        assert state["customer_id"] == "CUST-001"
        assert state["change_type"] == "LEGAL_NAME"
        assert state["document_type"] == "MARRIAGE_CERTIFICATE"
        assert state["document_path"] == "/tmp/doc.pdf"
        assert state["requested_old_value"] == "John Doe"
        assert state["requested_new_value"] == "John Smith"
        assert state["flags"] == []
        assert state["validation_passed"] is False

    def test_create_initial_state_defaults(self):
        """Test create_initial_state has correct default values."""
        state = create_initial_state(
            request_id="test-123",
            customer_id="CUST-001",
            change_type="ADDRESS",
            document_type="UTILITY_BILL",
            document_path="/tmp/doc.pdf",
            requested_old_value="123 Old St",
            requested_new_value="456 New Ave",
        )

        assert state["ocr_text"] == ""
        assert state["ocr_confidence"] == 0.0
        assert state["overall_score"] == 0.0
        assert state["risk_tier"] == ""
        assert state["ai_recommendation"] == ""
        assert state["errors"] == []


class TestDocumentProcessingPipeline:
    """Tests for DocumentProcessingPipeline class."""

    def test_pipeline_initialization(self):
        """Test pipeline can be initialized."""
        pipeline = DocumentProcessingPipeline()
        assert pipeline is not None
        assert pipeline.graph is not None

    @pytest.mark.asyncio
    async def test_pipeline_process_with_invalid_request(self):
        """Test pipeline handles invalid request gracefully."""
        pipeline = DocumentProcessingPipeline()

        result = await pipeline.process(
            request_id="test-123",
            customer_id="CUST-001",
            change_type="LEGAL_NAME",
            document_type="MARRIAGE_CERTIFICATE",
            document_path="/nonexistent/path.pdf",
            requested_old_value="John Doe",
            requested_new_value="John Smith",
        )

        assert result["validation_passed"] is False
        assert len(result.get("validation_errors", [])) > 0

    def test_pipeline_graph_visualization(self):
        """Test pipeline graph visualization method."""
        pipeline = DocumentProcessingPipeline()
        viz = pipeline.get_graph_visualization()

        assert "validation" in viz
        assert "ocr" in viz
        assert "classifier" in viz
        assert "scorer" in viz
        assert "END" in viz
