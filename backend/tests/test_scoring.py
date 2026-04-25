"""
Tests for scoring and name matching algorithms.
"""

import pytest
from app.agents.nodes.scorer import calculate_name_match, scorer_node


class TestNameMatching:
    """Tests for name matching algorithms."""

    def test_exact_match(self):
        """Test exact name match."""
        score = calculate_name_match("John Smith", "John Smith")
        assert score == 1.0

    def test_case_insensitive_match(self):
        """Test case insensitive matching."""
        score = calculate_name_match("JOHN SMITH", "john smith")
        assert score >= 0.95

    def test_minor_typo(self):
        """Test handling of minor typos."""
        score = calculate_name_match("John Smth", "John Smith")
        assert 0.85 <= score <= 0.99

    def test_completely_different_names(self):
        """Test completely different names."""
        score = calculate_name_match("John Smith", "Jane Doe")
        assert score < 0.7

    def test_name_with_middle_name(self):
        """Test names with/without middle names."""
        score = calculate_name_match("John A Smith", "John Smith")
        assert score >= 0.7

    def test_reversed_name_order(self):
        """Test reversed name order."""
        score = calculate_name_match("Smith, John", "John Smith")
        assert score >= 0.5

    def test_abbreviated_first_name(self):
        """Test abbreviated first names."""
        score = calculate_name_match("J. Smith", "John Smith")
        assert score >= 0.6

    def test_hyphenated_names(self):
        """Test hyphenated names."""
        score = calculate_name_match("Mary-Jane Watson", "Mary Jane Watson")
        assert score >= 0.9

    def test_empty_names(self):
        """Test empty name handling."""
        assert calculate_name_match("", "John Smith") == 0.0
        assert calculate_name_match("John Smith", "") == 0.0
        assert calculate_name_match("", "") == 0.0
        assert calculate_name_match(None, "John Smith") == 0.0


class TestScorerNode:
    """Tests for scorer node processing."""

    @pytest.mark.asyncio
    async def test_scorer_node_basic(self):
        """Test basic scorer node processing."""
        state = {
            "request_id": "test-123",
            "extracted_old_value": "John Doe",
            "extracted_new_value": "John Smith",
            "requested_old_value": "John Doe",
            "requested_new_value": "John Smith",
            "forgery_score": 0.95,
            "ocr_confidence": 0.92,
            "extraction_confidence": 0.90,
            "flags": [],
        }

        result = await scorer_node(state)

        assert "overall_score" in result
        assert "risk_tier" in result
        assert "old_name_match_score" in result
        assert "new_name_match_score" in result
        assert "field_scores" in result
        assert result["current_step"] == "scorer"

    @pytest.mark.asyncio
    async def test_scorer_node_perfect_match(self):
        """Test scorer with perfect name matches."""
        state = {
            "request_id": "test-123",
            "extracted_old_value": "John Doe",
            "extracted_new_value": "John Smith",
            "requested_old_value": "John Doe",
            "requested_new_value": "John Smith",
            "forgery_score": 0.95,
            "ocr_confidence": 0.95,
            "extraction_confidence": 0.95,
            "flags": [],
        }

        result = await scorer_node(state)

        assert result["old_name_match_score"] == 1.0
        assert result["new_name_match_score"] == 1.0
        assert result["overall_score"] >= 0.9
        assert result["risk_tier"] == "LOW"

    @pytest.mark.asyncio
    async def test_scorer_node_low_confidence(self):
        """Test scorer with low confidence scores."""
        state = {
            "request_id": "test-123",
            "extracted_old_value": "Jon Doe",
            "extracted_new_value": "J Smith",
            "requested_old_value": "John Doe",
            "requested_new_value": "John Smith",
            "forgery_score": 0.50,
            "ocr_confidence": 0.55,
            "extraction_confidence": 0.50,
            "flags": [],
        }

        result = await scorer_node(state)

        assert result["overall_score"] < 0.9
        assert result["risk_tier"] in ["MEDIUM", "HIGH"]

    @pytest.mark.asyncio
    async def test_scorer_node_name_mismatch_flags(self):
        """Test that name mismatches add appropriate flags."""
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

        assert any("MISMATCH" in flag or "FUZZY" in flag for flag in result["flags"])

    @pytest.mark.asyncio
    async def test_scorer_node_field_scores_structure(self):
        """Test field_scores has correct structure."""
        state = {
            "request_id": "test-123",
            "extracted_old_value": "John Doe",
            "extracted_new_value": "John Smith",
            "requested_old_value": "John Doe",
            "requested_new_value": "John Smith",
            "forgery_score": 0.95,
            "ocr_confidence": 0.92,
            "extraction_confidence": 0.90,
            "flags": [],
        }

        result = await scorer_node(state)

        assert len(result["field_scores"]) == 2

        for field_score in result["field_scores"]:
            assert "field" in field_score
            assert "extracted" in field_score
            assert "expected" in field_score
            assert "score" in field_score
            assert "method" in field_score
            assert isinstance(field_score["score"], float)

    @pytest.mark.asyncio
    async def test_scorer_node_preserves_existing_flags(self):
        """Test that existing flags are preserved."""
        state = {
            "request_id": "test-123",
            "extracted_old_value": "John Doe",
            "extracted_new_value": "John Smith",
            "requested_old_value": "John Doe",
            "requested_new_value": "John Smith",
            "forgery_score": 0.95,
            "ocr_confidence": 0.92,
            "extraction_confidence": 0.90,
            "flags": ["EXISTING_FLAG"],
        }

        result = await scorer_node(state)

        assert "EXISTING_FLAG" in result["flags"]

    @pytest.mark.asyncio
    async def test_scorer_node_major_flag_forces_high_risk(self):
        """Test that major flags force HIGH risk tier."""
        state = {
            "request_id": "test-123",
            "extracted_old_value": "John Doe",
            "extracted_new_value": "John Smith",
            "requested_old_value": "John Doe",
            "requested_new_value": "John Smith",
            "forgery_score": 0.95,
            "ocr_confidence": 0.95,
            "extraction_confidence": 0.95,
            "flags": ["FORGERY_FLAG"],
        }

        result = await scorer_node(state)

        assert result["risk_tier"] == "HIGH"

    @pytest.mark.asyncio
    async def test_scorer_node_missing_values_defaults(self):
        """Test scorer handles missing state values with defaults."""
        state = {
            "request_id": "test-123",
        }

        result = await scorer_node(state)

        assert "overall_score" in result
        assert "risk_tier" in result
        assert result["old_name_match_score"] == 0.0
        assert result["new_name_match_score"] == 0.0
