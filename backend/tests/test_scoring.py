"""
Tests for scoring and name matching algorithms.
"""

import pytest
from app.agents.nodes.scorer import ScorerNode


class TestNameMatching:
    """Tests for name matching algorithms."""

    @pytest.mark.asyncio
    async def test_exact_match(self):
        """Test exact name match."""
        node = ScorerNode()
        score = node._calculate_name_match_score("John Smith", "John Smith")
        assert score == 1.0

    @pytest.mark.asyncio
    async def test_case_insensitive_match(self):
        """Test case insensitive matching."""
        node = ScorerNode()
        score = node._calculate_name_match_score("JOHN SMITH", "john smith")
        assert score >= 0.95

    @pytest.mark.asyncio
    async def test_minor_typo(self):
        """Test handling of minor typos."""
        node = ScorerNode()
        score = node._calculate_name_match_score("John Smth", "John Smith")
        assert 0.85 <= score <= 0.95

    @pytest.mark.asyncio
    async def test_completely_different_names(self):
        """Test completely different names."""
        node = ScorerNode()
        score = node._calculate_name_match_score("John Smith", "Jane Doe")
        assert score < 0.5

    @pytest.mark.asyncio
    async def test_name_with_middle_name(self):
        """Test names with/without middle names."""
        node = ScorerNode()
        score = node._calculate_name_match_score("John A Smith", "John Smith")
        assert score >= 0.7

    @pytest.mark.asyncio
    async def test_reversed_name_order(self):
        """Test reversed name order."""
        node = ScorerNode()
        score = node._calculate_name_match_score("Smith, John", "John Smith")
        # Should have reasonable match if algorithm handles this
        assert score >= 0.5

    @pytest.mark.asyncio
    async def test_abbreviated_first_name(self):
        """Test abbreviated first names."""
        node = ScorerNode()
        score = node._calculate_name_match_score("J. Smith", "John Smith")
        assert score >= 0.6

    @pytest.mark.asyncio
    async def test_hyphenated_names(self):
        """Test hyphenated names."""
        node = ScorerNode()
        score = node._calculate_name_match_score(
            "Mary-Jane Watson", "Mary Jane Watson"
        )
        assert score >= 0.9


class TestAddressMatching:
    """Tests for address matching."""

    @pytest.mark.asyncio
    async def test_exact_address_match(self):
        """Test exact address match."""
        node = ScorerNode()
        address = "123 Main Street, Apt 4B, New York, NY 10001"
        score = node._calculate_address_match_score(address, address)
        assert score == 1.0

    @pytest.mark.asyncio
    async def test_address_abbreviations(self):
        """Test address abbreviations."""
        node = ScorerNode()
        score = node._calculate_address_match_score(
            "123 Main St, New York, NY",
            "123 Main Street, New York, New York",
        )
        assert score >= 0.8

    @pytest.mark.asyncio
    async def test_missing_zip_code(self):
        """Test address with missing zip code."""
        node = ScorerNode()
        score = node._calculate_address_match_score(
            "123 Main Street, New York, NY",
            "123 Main Street, New York, NY 10001",
        )
        assert score >= 0.85

    @pytest.mark.asyncio
    async def test_different_addresses(self):
        """Test completely different addresses."""
        node = ScorerNode()
        score = node._calculate_address_match_score(
            "123 Main Street, New York",
            "456 Oak Avenue, Los Angeles",
        )
        assert score < 0.5


class TestOverallScoring:
    """Tests for overall score calculation."""

    @pytest.mark.asyncio
    async def test_high_confidence_scoring(self):
        """Test scoring for high confidence case."""
        node = ScorerNode()

        result = node._calculate_overall_score(
            name_match_score=1.0,
            doc_authenticity_score=0.95,
            ocr_confidence=0.98,
            extraction_confidence=0.96,
        )

        assert result >= 0.9

    @pytest.mark.asyncio
    async def test_low_confidence_scoring(self):
        """Test scoring for low confidence case."""
        node = ScorerNode()

        result = node._calculate_overall_score(
            name_match_score=0.5,
            doc_authenticity_score=0.4,
            ocr_confidence=0.55,
            extraction_confidence=0.50,
        )

        assert result < 0.7

    @pytest.mark.asyncio
    async def test_weight_distribution(self):
        """Test that weights are applied correctly."""
        node = ScorerNode()

        # Name match has highest weight (40%)
        high_name_score = node._calculate_overall_score(
            name_match_score=1.0,
            doc_authenticity_score=0.0,
            ocr_confidence=0.0,
            extraction_confidence=0.0,
        )

        low_name_score = node._calculate_overall_score(
            name_match_score=0.0,
            doc_authenticity_score=1.0,
            ocr_confidence=1.0,
            extraction_confidence=1.0,
        )

        # High name score should contribute ~0.4
        assert high_name_score >= 0.35

    @pytest.mark.asyncio
    async def test_risk_tier_assignment_low(self):
        """Test LOW risk tier assignment."""
        node = ScorerNode()

        result = node._determine_risk_tier(0.95)
        assert result.value == "LOW"

    @pytest.mark.asyncio
    async def test_risk_tier_assignment_medium(self):
        """Test MEDIUM risk tier assignment."""
        node = ScorerNode()

        result = node._determine_risk_tier(0.80)
        assert result.value == "MEDIUM"

    @pytest.mark.asyncio
    async def test_risk_tier_assignment_high(self):
        """Test HIGH risk tier assignment."""
        node = ScorerNode()

        result = node._determine_risk_tier(0.65)
        assert result.value == "HIGH"

    @pytest.mark.asyncio
    async def test_recommendation_approve(self):
        """Test APPROVE recommendation."""
        node = ScorerNode()

        result = node._determine_recommendation(
            overall_score=0.95,
            forgery_score=0.05,
            flags=[],
        )
        assert result.value == "APPROVE"

    @pytest.mark.asyncio
    async def test_recommendation_reject_low_score(self):
        """Test REJECT recommendation for low score."""
        node = ScorerNode()

        result = node._determine_recommendation(
            overall_score=0.40,
            forgery_score=0.70,
            flags=["potential_forgery"],
        )
        assert result.value == "REJECT"

    @pytest.mark.asyncio
    async def test_recommendation_manual_review(self):
        """Test MANUAL_REVIEW recommendation."""
        node = ScorerNode()

        result = node._determine_recommendation(
            overall_score=0.75,
            forgery_score=0.25,
            flags=["low_ocr_confidence"],
        )
        assert result.value == "MANUAL_REVIEW"

    @pytest.mark.asyncio
    async def test_flags_affect_recommendation(self):
        """Test that flags can force manual review."""
        node = ScorerNode()

        # High score but with flags
        result = node._determine_recommendation(
            overall_score=0.92,
            forgery_score=0.10,
            flags=["document_type_mismatch"],
        )
        # Should require manual review despite high score
        assert result.value in ["MANUAL_REVIEW", "REJECT"]
