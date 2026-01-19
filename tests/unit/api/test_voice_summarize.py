"""
Unit tests for /voice/summarize endpoint.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.api.auth.tokens import create_access_token


@pytest.fixture
def auth_headers():
    """Generate auth headers with a valid token."""
    token = create_access_token("test-user")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_lm_result():
    """Mock the DSPy LM result."""
    mock_result = MagicMock()
    mock_result.goal = "A brave little dragon learns to make friends"
    mock_result.summary = "I'll create a story about a shy dragon who overcomes fear to befriend other creatures."
    return mock_result


class TestVoiceSummarize:
    """Tests for /voice/summarize endpoint."""

    def test_summarize_extracts_goal_from_transcript(self, client, auth_headers, mock_lm_result):
        """Should extract a clean story goal from rambling transcript."""
        with patch('backend.api.routes.voice.summarize.get_inference_lm'), \
             patch('backend.api.routes.voice.summarize.dspy.Predict') as mock_predict:
            # Setup mocks
            mock_predict.return_value.return_value = mock_lm_result

            response = client.post(
                "/voice/summarize",
                json={"transcript": "um so I want like a story about um a dragon who is shy and learns to make friends"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "goal" in data
            assert "summary" in data
            assert data["goal"] == "A brave little dragon learns to make friends"
            assert "I'll create" in data["summary"]

    def test_summarize_requires_transcript(self, client, auth_headers):
        """Should return 422 if transcript missing."""
        response = client.post(
            "/voice/summarize",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_summarize_rejects_empty_transcript(self, client, auth_headers):
        """Should return 400 if transcript is empty."""
        response = client.post(
            "/voice/summarize",
            json={"transcript": "   "},
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_summarize_requires_auth(self, client):
        """Should return 401 without auth."""
        response = client.post(
            "/voice/summarize",
            json={"transcript": "a story about dragons"},
        )
        assert response.status_code == 401
