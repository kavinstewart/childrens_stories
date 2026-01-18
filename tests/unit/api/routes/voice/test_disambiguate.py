"""Unit tests for homograph disambiguation endpoint."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.api.routes.voice.disambiguate import (
    DisambiguateRequest,
    DisambiguateResponse,
    disambiguate_homograph,
    parse_llm_response,
)


class TestParseLlmResponse:
    """Tests for parsing LLM responses."""

    def test_parse_direct_zero(self):
        assert parse_llm_response("0") == 0

    def test_parse_direct_one(self):
        assert parse_llm_response("1") == 1

    def test_parse_with_whitespace(self):
        assert parse_llm_response("  0  ") == 0
        assert parse_llm_response("\n1\n") == 1

    def test_parse_with_prefix(self):
        assert parse_llm_response("0) The first option") == 0
        assert parse_llm_response("1 - second meaning") == 1

    def test_parse_embedded_number(self):
        assert parse_llm_response("The answer is 0.") == 0
        assert parse_llm_response("I choose 1 because...") == 1

    def test_parse_invalid_returns_none(self):
        assert parse_llm_response("invalid") is None
        assert parse_llm_response("two") is None
        assert parse_llm_response("") is None


class TestDisambiguateEndpoint:
    """Tests for the disambiguation endpoint."""

    @pytest.fixture
    def mock_lm(self):
        """Create a mock language model."""
        lm = MagicMock()
        lm.return_value = MagicMock(completions="0")
        return lm

    @pytest.mark.asyncio
    async def test_disambiguate_returns_pronunciation_index(self):
        """Test that endpoint returns correct pronunciation index."""
        request = DisambiguateRequest(word="read", sentence="I read books every day.")

        with patch(
            "backend.api.routes.voice.disambiguate.get_inference_lm"
        ) as mock_get_lm:
            mock_lm = MagicMock()
            mock_get_lm.return_value = mock_lm

            with patch("dspy.Predict") as mock_predict:
                mock_predictor = MagicMock()
                mock_predictor.return_value = MagicMock(answer="0")
                mock_predict.return_value = mock_predictor

                response = await disambiguate_homograph(
                    request=request, current_user="test-user"
                )

        assert isinstance(response, DisambiguateResponse)
        assert response.word == "read"
        assert response.pronunciation_index in (0, 1)

    @pytest.mark.asyncio
    async def test_disambiguate_unknown_word_returns_default(self):
        """Test that unknown words return default pronunciation (0)."""
        request = DisambiguateRequest(word="cat", sentence="The cat sat on the mat.")

        response = await disambiguate_homograph(
            request=request, current_user="test-user"
        )

        assert response.word == "cat"
        assert response.pronunciation_index == 0
        assert response.is_homograph is False

    @pytest.mark.asyncio
    async def test_disambiguate_includes_phonemes(self):
        """Test that response includes phonemes for known homographs."""
        request = DisambiguateRequest(word="read", sentence="I read books every day.")

        with patch(
            "backend.api.routes.voice.disambiguate.get_inference_lm"
        ) as mock_get_lm:
            mock_lm = MagicMock()
            mock_get_lm.return_value = mock_lm

            with patch("dspy.Predict") as mock_predict:
                mock_predictor = MagicMock()
                mock_predictor.return_value = MagicMock(answer="0")
                mock_predict.return_value = mock_predictor

                response = await disambiguate_homograph(
                    request=request, current_user="test-user"
                )

        assert response.is_homograph is True
        assert response.phonemes is not None
        assert "|" in response.phonemes  # IPA pipe-separated format

    @pytest.mark.asyncio
    async def test_disambiguate_with_occurrence(self):
        """Test disambiguation with specific word occurrence."""
        request = DisambiguateRequest(
            word="bass",
            sentence="The bass player caught a bass.",
            occurrence=2,  # Second "bass" = the fish
        )

        with patch(
            "backend.api.routes.voice.disambiguate.get_inference_lm"
        ) as mock_get_lm:
            mock_lm = MagicMock()
            mock_get_lm.return_value = mock_lm

            with patch("dspy.Predict") as mock_predict:
                mock_predictor = MagicMock()
                mock_predictor.return_value = MagicMock(answer="1")
                mock_predict.return_value = mock_predictor

                response = await disambiguate_homograph(
                    request=request, current_user="test-user"
                )

        assert response.pronunciation_index == 1


class TestDisambiguateRequest:
    """Tests for request validation."""

    def test_valid_request(self):
        request = DisambiguateRequest(word="read", sentence="I read a book.")
        assert request.word == "read"
        assert request.sentence == "I read a book."
        assert request.occurrence == 1

    def test_default_occurrence(self):
        request = DisambiguateRequest(word="read", sentence="I read a book.")
        assert request.occurrence == 1

    def test_custom_occurrence(self):
        request = DisambiguateRequest(
            word="read", sentence="I read what you read.", occurrence=2
        )
        assert request.occurrence == 2
