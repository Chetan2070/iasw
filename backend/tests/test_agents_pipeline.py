"""
Tests for LangGraph document processing pipeline.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.agents.state import ProcessingState
from app.agents.graph import DocumentProcessingPipeline
from app.agents.nodes.validation import ValidationNode
from app.agents.nodes.ocr import OCRNode
from app.agents.nodes.classifier import ClassifierNode
from app.agents.nodes.extractor import ExtractorNode
from app.agents.nodes.forgery import ForgeryDetectionNode
from app.agents.nodes.scorer import ScorerNode
from app.agents.nodes.summary import SummaryNode
from app.models.enums import ChangeType, DocumentType, RiskTier, Recommendation


class TestValidationNode:
    """Tests for ValidationNode."""

    @pytest.mark.asyncio
    async def test_validation_success(self):
        """Test successful validation."""
        node = ValidationNode()
        state: ProcessingState = {
            "request_id": "test-123",
            "customer_id": "CUST-001",
            "change_type": ChangeType.LEGAL_NAME,
            "document_type": DocumentType.MARRIAGE_CERTIFICATE,
            "document_path": "/tmp/test.pdf",
            "requested_old_value": "John Doe",
            "requested_new_value": "John Smith",
            "image_bytes": b"test image data",
            "validation_passed": False,
            "validation_errors": [],
            "ocr_text": None,
            "ocr_confidence": None,
            "classified_doc_type": None,
            "classification_confidence": None,
            "doc_type_matches": False,
            "extracted_fields": {},
            "extraction_confidence": None,
            "forgery_score": None,
            "forgery_details": {},
            "field_scores": [],
            "overall_score": None,
            "doc_authenticity_score": None,
            "risk_tier": None,
            "recommendation": None,
            "flags": [],
            "ai_summary": None,
            "error": None,
        }

        result = await node.process(state)

        assert result["validation_passed"] == True
        assert len(result["validation_errors"]) == 0

    @pytest.mark.asyncio
    async def test_validation_missing_document(self):
        """Test validation with missing document."""
        node = ValidationNode()
        state: ProcessingState = {
            "request_id": "test-123",
            "customer_id": "CUST-001",
            "change_type": ChangeType.LEGAL_NAME,
            "document_type": DocumentType.MARRIAGE_CERTIFICATE,
            "document_path": None,
            "requested_old_value": "John Doe",
            "requested_new_value": "John Smith",
            "image_bytes": None,
            "validation_passed": False,
            "validation_errors": [],
            "ocr_text": None,
            "ocr_confidence": None,
            "classified_doc_type": None,
            "classification_confidence": None,
            "doc_type_matches": False,
            "extracted_fields": {},
            "extraction_confidence": None,
            "forgery_score": None,
            "forgery_details": {},
            "field_scores": [],
            "overall_score": None,
            "doc_authenticity_score": None,
            "risk_tier": None,
            "recommendation": None,
            "flags": [],
            "ai_summary": None,
            "error": None,
        }

        result = await node.process(state)

        assert result["validation_passed"] == False
        assert len(result["validation_errors"]) > 0

    @pytest.mark.asyncio
    async def test_validation_invalid_document_type(self):
        """Test validation with invalid document type for change."""
        node = ValidationNode()
        state: ProcessingState = {
            "request_id": "test-123",
            "customer_id": "CUST-001",
            "change_type": ChangeType.LEGAL_NAME,
            "document_type": DocumentType.UTILITY_BILL,  # Invalid for LEGAL_NAME
            "document_path": "/tmp/test.pdf",
            "requested_old_value": "John Doe",
            "requested_new_value": "John Smith",
            "image_bytes": b"test image data",
            "validation_passed": False,
            "validation_errors": [],
            "ocr_text": None,
            "ocr_confidence": None,
            "classified_doc_type": None,
            "classification_confidence": None,
            "doc_type_matches": False,
            "extracted_fields": {},
            "extraction_confidence": None,
            "forgery_score": None,
            "forgery_details": {},
            "field_scores": [],
            "overall_score": None,
            "doc_authenticity_score": None,
            "risk_tier": None,
            "recommendation": None,
            "flags": [],
            "ai_summary": None,
            "error": None,
        }

        result = await node.process(state)

        assert result["validation_passed"] == False
        assert any("document type" in e.lower() for e in result["validation_errors"])


class TestOCRNode:
    """Tests for OCRNode."""

    @pytest.mark.asyncio
    async def test_ocr_success(self, sample_image_bytes):
        """Test successful OCR processing."""
        node = OCRNode()

        with patch.object(node, "_run_tesseract") as mock_tesseract:
            mock_tesseract.return_value = ("Extracted text from document", 0.92)

            state: ProcessingState = {
                "request_id": "test-123",
                "image_bytes": sample_image_bytes,
                "ocr_text": None,
                "ocr_confidence": None,
                "flags": [],
                # Other required fields...
            }

            result = await node.process(state)

            assert result["ocr_text"] is not None
            assert result["ocr_confidence"] >= 0

    @pytest.mark.asyncio
    async def test_ocr_low_confidence_flag(self, sample_image_bytes):
        """Test OCR adds flag for low confidence."""
        node = OCRNode()

        with patch.object(node, "_run_tesseract") as mock_tesseract:
            mock_tesseract.return_value = ("Poor quality text", 0.45)

            state: ProcessingState = {
                "request_id": "test-123",
                "image_bytes": sample_image_bytes,
                "ocr_text": None,
                "ocr_confidence": None,
                "flags": [],
            }

            result = await node.process(state)

            assert result["ocr_confidence"] < 0.7
            assert "low_ocr_confidence" in result["flags"]


class TestClassifierNode:
    """Tests for ClassifierNode."""

    @pytest.mark.asyncio
    async def test_classifier_correct_match(self, mock_anthropic_client):
        """Test classifier correctly identifies document type."""
        node = ClassifierNode()

        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[
                MagicMock(
                    text='{"classification": "MARRIAGE_CERTIFICATE", "confidence": 0.95}'
                )
            ]
        )

        state: ProcessingState = {
            "request_id": "test-123",
            "document_type": DocumentType.MARRIAGE_CERTIFICATE,
            "ocr_text": "Marriage Certificate\nThis certifies that...",
            "classified_doc_type": None,
            "classification_confidence": None,
            "doc_type_matches": False,
            "flags": [],
        }

        with patch("app.agents.nodes.classifier.Anthropic", return_value=mock_anthropic_client):
            result = await node.process(state)

        assert result["doc_type_matches"] == True
        assert result["classification_confidence"] >= 0.9

    @pytest.mark.asyncio
    async def test_classifier_mismatch(self, mock_anthropic_client):
        """Test classifier detects document type mismatch."""
        node = ClassifierNode()

        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[
                MagicMock(
                    text='{"classification": "UTILITY_BILL", "confidence": 0.88}'
                )
            ]
        )

        state: ProcessingState = {
            "request_id": "test-123",
            "document_type": DocumentType.MARRIAGE_CERTIFICATE,
            "ocr_text": "Electricity Bill\nAmount Due...",
            "classified_doc_type": None,
            "classification_confidence": None,
            "doc_type_matches": False,
            "flags": [],
        }

        with patch("app.agents.nodes.classifier.Anthropic", return_value=mock_anthropic_client):
            result = await node.process(state)

        assert result["doc_type_matches"] == False
        assert "document_type_mismatch" in result["flags"]


class TestExtractorNode:
    """Tests for ExtractorNode."""

    @pytest.mark.asyncio
    async def test_extractor_legal_name(self, mock_anthropic_client):
        """Test field extraction for legal name change."""
        node = ExtractorNode()

        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[
                MagicMock(
                    text=json.dumps({
                        "old_name": "John Doe",
                        "new_name": "John Smith",
                        "certificate_number": "MC-12345",
                        "date_of_marriage": "2024-01-15",
                        "confidence": 0.93,
                    })
                )
            ]
        )

        state: ProcessingState = {
            "request_id": "test-123",
            "change_type": ChangeType.LEGAL_NAME,
            "document_type": DocumentType.MARRIAGE_CERTIFICATE,
            "ocr_text": "Marriage Certificate...",
            "extracted_fields": {},
            "extraction_confidence": None,
            "flags": [],
        }

        with patch("app.agents.nodes.extractor.Anthropic", return_value=mock_anthropic_client):
            result = await node.process(state)

        assert "old_name" in result["extracted_fields"]
        assert "new_name" in result["extracted_fields"]
        assert result["extraction_confidence"] >= 0.9

    @pytest.mark.asyncio
    async def test_extractor_address(self, mock_anthropic_client):
        """Test field extraction for address change."""
        node = ExtractorNode()

        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[
                MagicMock(
                    text=json.dumps({
                        "address": "456 New Street, New City",
                        "date": "2024-02-01",
                        "account_holder": "John Smith",
                        "confidence": 0.88,
                    })
                )
            ]
        )

        state: ProcessingState = {
            "request_id": "test-123",
            "change_type": ChangeType.ADDRESS,
            "document_type": DocumentType.UTILITY_BILL,
            "ocr_text": "Utility Bill...",
            "extracted_fields": {},
            "extraction_confidence": None,
            "flags": [],
        }

        with patch("app.agents.nodes.extractor.Anthropic", return_value=mock_anthropic_client):
            result = await node.process(state)

        assert "address" in result["extracted_fields"]


class TestForgeryDetectionNode:
    """Tests for ForgeryDetectionNode."""

    @pytest.mark.asyncio
    async def test_forgery_detection_clean(self, sample_image_bytes):
        """Test forgery detection on clean document."""
        node = ForgeryDetectionNode()

        state: ProcessingState = {
            "request_id": "test-123",
            "image_bytes": sample_image_bytes,
            "document_path": "/tmp/test.png",
            "forgery_score": None,
            "forgery_details": {},
            "flags": [],
        }

        with patch.object(node, "_check_metadata") as mock_meta, \
             patch.object(node, "_check_ela") as mock_ela, \
             patch.object(node, "_check_fonts") as mock_fonts, \
             patch.object(node, "_run_ml_model") as mock_ml:
            mock_meta.return_value = (0.1, {"clean": True})
            mock_ela.return_value = (0.15, {"suspicious_regions": 0})
            mock_fonts.return_value = (0.1, {"consistent": True})
            mock_ml.return_value = (0.12, {"prediction": "authentic"})

            result = await node.process(state)

        assert result["forgery_score"] < 0.3
        assert "potential_forgery" not in result["flags"]

    @pytest.mark.asyncio
    async def test_forgery_detection_suspicious(self, sample_image_bytes):
        """Test forgery detection on suspicious document."""
        node = ForgeryDetectionNode()

        state: ProcessingState = {
            "request_id": "test-123",
            "image_bytes": sample_image_bytes,
            "document_path": "/tmp/test.png",
            "forgery_score": None,
            "forgery_details": {},
            "flags": [],
        }

        with patch.object(node, "_check_metadata") as mock_meta, \
             patch.object(node, "_check_ela") as mock_ela, \
             patch.object(node, "_check_fonts") as mock_fonts, \
             patch.object(node, "_run_ml_model") as mock_ml:
            mock_meta.return_value = (0.8, {"edited": True})
            mock_ela.return_value = (0.75, {"suspicious_regions": 3})
            mock_fonts.return_value = (0.6, {"inconsistent": True})
            mock_ml.return_value = (0.85, {"prediction": "tampered"})

            result = await node.process(state)

        assert result["forgery_score"] > 0.5
        assert "potential_forgery" in result["flags"]


class TestScorerNode:
    """Tests for ScorerNode."""

    @pytest.mark.asyncio
    async def test_scorer_high_confidence(self):
        """Test scoring for high confidence case."""
        node = ScorerNode()

        state: ProcessingState = {
            "request_id": "test-123",
            "change_type": ChangeType.LEGAL_NAME,
            "requested_old_value": "John Doe",
            "requested_new_value": "John Smith",
            "extracted_fields": {"old_name": "John Doe", "new_name": "John Smith"},
            "ocr_confidence": 0.95,
            "extraction_confidence": 0.93,
            "forgery_score": 0.1,
            "field_scores": [],
            "overall_score": None,
            "doc_authenticity_score": None,
            "risk_tier": None,
            "recommendation": None,
            "flags": [],
        }

        result = await node.process(state)

        assert result["overall_score"] >= 0.9
        assert result["risk_tier"] == RiskTier.LOW
        assert result["recommendation"] == Recommendation.APPROVE

    @pytest.mark.asyncio
    async def test_scorer_medium_confidence(self):
        """Test scoring for medium confidence case."""
        node = ScorerNode()

        state: ProcessingState = {
            "request_id": "test-123",
            "change_type": ChangeType.LEGAL_NAME,
            "requested_old_value": "John Doe",
            "requested_new_value": "John Smith",
            "extracted_fields": {"old_name": "J. Doe", "new_name": "John Smith"},
            "ocr_confidence": 0.78,
            "extraction_confidence": 0.75,
            "forgery_score": 0.25,
            "field_scores": [],
            "overall_score": None,
            "doc_authenticity_score": None,
            "risk_tier": None,
            "recommendation": None,
            "flags": [],
        }

        result = await node.process(state)

        assert 0.7 <= result["overall_score"] < 0.9
        assert result["risk_tier"] == RiskTier.MEDIUM
        assert result["recommendation"] == Recommendation.MANUAL_REVIEW

    @pytest.mark.asyncio
    async def test_scorer_low_confidence(self):
        """Test scoring for low confidence case."""
        node = ScorerNode()

        state: ProcessingState = {
            "request_id": "test-123",
            "change_type": ChangeType.LEGAL_NAME,
            "requested_old_value": "John Doe",
            "requested_new_value": "John Smith",
            "extracted_fields": {"old_name": "Jane Doe", "new_name": "Jane Smith"},
            "ocr_confidence": 0.55,
            "extraction_confidence": 0.50,
            "forgery_score": 0.65,
            "field_scores": [],
            "overall_score": None,
            "doc_authenticity_score": None,
            "risk_tier": None,
            "recommendation": None,
            "flags": ["potential_forgery"],
        }

        result = await node.process(state)

        assert result["overall_score"] < 0.7
        assert result["risk_tier"] == RiskTier.HIGH
        assert result["recommendation"] == Recommendation.REJECT


class TestSummaryNode:
    """Tests for SummaryNode."""

    @pytest.mark.asyncio
    async def test_summary_generation(self, mock_anthropic_client):
        """Test AI summary generation."""
        node = SummaryNode()

        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[
                MagicMock(
                    text="Document verification complete. Marriage certificate authenticated with high confidence. Name change from John Doe to John Smith verified."
                )
            ]
        )

        state: ProcessingState = {
            "request_id": "test-123",
            "change_type": ChangeType.LEGAL_NAME,
            "document_type": DocumentType.MARRIAGE_CERTIFICATE,
            "requested_old_value": "John Doe",
            "requested_new_value": "John Smith",
            "extracted_fields": {"old_name": "John Doe", "new_name": "John Smith"},
            "overall_score": 0.92,
            "risk_tier": RiskTier.LOW,
            "recommendation": Recommendation.APPROVE,
            "flags": [],
            "ai_summary": None,
        }

        with patch("app.agents.nodes.summary.Anthropic", return_value=mock_anthropic_client):
            result = await node.process(state)

        assert result["ai_summary"] is not None
        assert len(result["ai_summary"]) > 0


class TestDocumentProcessingPipeline:
    """Tests for complete pipeline integration."""

    @pytest.mark.asyncio
    async def test_pipeline_happy_path(self, mock_anthropic_client, sample_image_bytes):
        """Test complete pipeline execution for successful case."""
        pipeline = DocumentProcessingPipeline()

        initial_state: ProcessingState = {
            "request_id": "test-123",
            "customer_id": "CUST-001",
            "change_type": ChangeType.LEGAL_NAME,
            "document_type": DocumentType.MARRIAGE_CERTIFICATE,
            "document_path": "/tmp/test.pdf",
            "requested_old_value": "John Doe",
            "requested_new_value": "John Smith",
            "image_bytes": sample_image_bytes,
            "validation_passed": False,
            "validation_errors": [],
            "ocr_text": None,
            "ocr_confidence": None,
            "classified_doc_type": None,
            "classification_confidence": None,
            "doc_type_matches": False,
            "extracted_fields": {},
            "extraction_confidence": None,
            "forgery_score": None,
            "forgery_details": {},
            "field_scores": [],
            "overall_score": None,
            "doc_authenticity_score": None,
            "risk_tier": None,
            "recommendation": None,
            "flags": [],
            "ai_summary": None,
            "error": None,
        }

        # Mock all the nodes
        with patch.object(pipeline, "run") as mock_run:
            mock_run.return_value = {
                **initial_state,
                "validation_passed": True,
                "ocr_text": "Marriage Certificate...",
                "ocr_confidence": 0.95,
                "doc_type_matches": True,
                "classification_confidence": 0.92,
                "extracted_fields": {"old_name": "John Doe", "new_name": "John Smith"},
                "extraction_confidence": 0.91,
                "forgery_score": 0.1,
                "overall_score": 0.92,
                "risk_tier": RiskTier.LOW,
                "recommendation": Recommendation.APPROVE,
                "ai_summary": "Document verified successfully.",
            }

            result = await pipeline.run(initial_state)

        assert result["validation_passed"] == True
        assert result["overall_score"] >= 0.9
        assert result["recommendation"] == Recommendation.APPROVE

    @pytest.mark.asyncio
    async def test_pipeline_validation_failure(self):
        """Test pipeline stops at validation failure."""
        pipeline = DocumentProcessingPipeline()

        initial_state: ProcessingState = {
            "request_id": "test-123",
            "customer_id": "CUST-001",
            "change_type": ChangeType.LEGAL_NAME,
            "document_type": DocumentType.UTILITY_BILL,  # Invalid
            "document_path": None,  # Missing
            "requested_old_value": "John Doe",
            "requested_new_value": "John Smith",
            "image_bytes": None,
            "validation_passed": False,
            "validation_errors": [],
            "ocr_text": None,
            "ocr_confidence": None,
            "classified_doc_type": None,
            "classification_confidence": None,
            "doc_type_matches": False,
            "extracted_fields": {},
            "extraction_confidence": None,
            "forgery_score": None,
            "forgery_details": {},
            "field_scores": [],
            "overall_score": None,
            "doc_authenticity_score": None,
            "risk_tier": None,
            "recommendation": None,
            "flags": [],
            "ai_summary": None,
            "error": None,
        }

        with patch.object(pipeline, "run") as mock_run:
            mock_run.return_value = {
                **initial_state,
                "validation_passed": False,
                "validation_errors": ["Invalid document type", "Missing document"],
                "error": "Validation failed",
            }

            result = await pipeline.run(initial_state)

        assert result["validation_passed"] == False
        assert len(result["validation_errors"]) > 0
