"""Unit tests for spread regeneration API endpoint."""

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from backend.api.models.enums import GenerationType, JobStatus
from backend.api.models.responses import StoryResponse, StorySpreadResponse


TEST_UUID = UUID("12345678-1234-5678-1234-567812345678")
TEST_UUID_STR = "12345678-1234-5678-1234-567812345678"
TEST_JOB_ID = "regen123"


def make_mock_story(is_illustrated: bool = True, spreads: list = None):
    """Create a mock story response for testing."""
    if spreads is None:
        spreads = [
            StorySpreadResponse(
                spread_number=i,
                text=f"Spread {i} text",
                word_count=40,
                illustration_prompt=f"Prompt for spread {i}",
            )
            for i in range(1, 13)
        ]

    return StoryResponse(
        id=TEST_UUID,
        status=JobStatus.COMPLETED,
        goal="teach about sharing",
        target_age_range="4-7",
        generation_type=GenerationType.ILLUSTRATED if is_illustrated else GenerationType.STANDARD,
        created_at=datetime.utcnow(),
        title="The Sharing Tree",
        word_count=500,
        spread_count=12,
        spreads=spreads,
    )


class TestRegenerateSpreadEndpoint:
    """Tests for POST /stories/{id}/spreads/{num}/regenerate endpoint."""

    def test_regenerate_spread_returns_202_accepted(self, client_with_mocks):
        """POST to valid story/spread returns 202 with job info."""
        client, mock_repo, mock_service = client_with_mocks

        mock_repo.get_story = AsyncMock(return_value=make_mock_story())
        mock_repo.get_spread = AsyncMock(return_value={
            "spread_number": 3,
            "text": "Test text",
            "illustration_prompt": "Test prompt",
        })
        mock_repo.get_active_spread_regen_job = AsyncMock(return_value=None)
        mock_service.regenerate_spread_job = AsyncMock(return_value=TEST_JOB_ID)

        response = client.post(f"/stories/{TEST_UUID_STR}/spreads/3/regenerate", json={})

        assert response.status_code == 202
        data = response.json()
        assert data["job_id"] == TEST_JOB_ID
        assert data["story_id"] == TEST_UUID_STR
        assert data["spread_number"] == 3
        assert data["status"] == "pending"

    def test_regenerate_spread_invalid_story_returns_404(self, client_with_mocks):
        """POST to non-existent story returns 404."""
        client, mock_repo, _ = client_with_mocks

        mock_repo.get_story = AsyncMock(return_value=None)

        response = client.post("/stories/nonexistent-id/spreads/1/regenerate", json={})

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_regenerate_spread_invalid_spread_returns_404(self, client_with_mocks):
        """POST to non-existent spread returns 404."""
        client, mock_repo, _ = client_with_mocks

        mock_repo.get_story = AsyncMock(return_value=make_mock_story())
        mock_repo.get_spread = AsyncMock(return_value=None)

        response = client.post(f"/stories/{TEST_UUID_STR}/spreads/99/regenerate", json={})

        assert response.status_code == 404
        assert "spread" in response.json()["detail"].lower()

    def test_regenerate_spread_non_illustrated_story_returns_400(self, client_with_mocks):
        """POST to non-illustrated story returns 400."""
        client, mock_repo, _ = client_with_mocks

        mock_repo.get_story = AsyncMock(return_value=make_mock_story(is_illustrated=False))

        response = client.post(f"/stories/{TEST_UUID_STR}/spreads/1/regenerate", json={})

        assert response.status_code == 400
        assert "non-illustrated" in response.json()["detail"].lower()

    def test_regenerate_spread_already_regenerating_returns_409(self, client_with_mocks):
        """POST when already regenerating returns 409 Conflict."""
        client, mock_repo, _ = client_with_mocks

        mock_repo.get_story = AsyncMock(return_value=make_mock_story())
        mock_repo.get_spread = AsyncMock(return_value={
            "spread_number": 3,
            "text": "Test text",
        })
        mock_repo.get_active_spread_regen_job = AsyncMock(return_value={
            "id": "existing",
            "status": "running",
        })

        response = client.post(f"/stories/{TEST_UUID_STR}/spreads/3/regenerate", json={})

        assert response.status_code == 409
        assert "already being regenerated" in response.json()["detail"].lower()

    def test_regenerate_spread_calls_service(self, client_with_mocks):
        """POST calls service.regenerate_spread_job with correct params."""
        client, mock_repo, mock_service = client_with_mocks

        mock_repo.get_story = AsyncMock(return_value=make_mock_story())
        mock_repo.get_spread = AsyncMock(return_value={
            "spread_number": 5,
            "text": "Test text",
        })
        mock_repo.get_active_spread_regen_job = AsyncMock(return_value=None)
        mock_service.regenerate_spread_job = AsyncMock(return_value=TEST_JOB_ID)

        response = client.post(f"/stories/{TEST_UUID_STR}/spreads/5/regenerate", json={})

        assert response.status_code == 202
        mock_service.regenerate_spread_job.assert_called_once_with(
            story_id=TEST_UUID_STR,
            spread_number=5,
        )
