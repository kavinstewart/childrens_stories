"""Integration tests for story API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime


class TestCreateStory:
    """Tests for POST /stories endpoint."""

    def test_create_story_returns_202_with_job_id(self, client_with_mocks):
        """Creating a story should return 202 Accepted with a job ID."""
        client, mock_repo, mock_service = client_with_mocks
        mock_service.create_story_job = AsyncMock(return_value="test-uuid-123")

        response = client.post(
            "/stories/",
            json={"goal": "teach about sharing"},
        )

        assert response.status_code == 202
        data = response.json()
        assert data["id"] == "test-uuid-123"
        assert data["status"] == "pending"

    def test_create_story_validates_goal_min_length(self, client_with_mocks):
        """Goal must be at least 3 characters."""
        client, _, _ = client_with_mocks

        response = client.post(
            "/stories/",
            json={"goal": "ab"},  # Too short
        )

        assert response.status_code == 422

    def test_create_story_validates_age_range_format(self, client_with_mocks):
        """Age range must match pattern 'min-max'."""
        client, _, _ = client_with_mocks

        response = client.post(
            "/stories/",
            json={"goal": "teach about sharing", "target_age_range": "invalid"},
        )

        assert response.status_code == 422

    def test_create_story_accepts_all_generation_types(self, client_with_mocks):
        """All three generation types should be accepted."""
        client, mock_repo, mock_service = client_with_mocks
        mock_service.create_story_job = AsyncMock(return_value="test-uuid")

        for gen_type in ["simple", "standard", "illustrated"]:
            response = client.post(
                "/stories/",
                json={"goal": "test goal", "generation_type": gen_type},
            )
            assert response.status_code == 202


class TestListStories:
    """Tests for GET /stories endpoint."""

    def test_list_stories_returns_empty_list(self, client_with_mocks):
        """Empty database should return empty list."""
        client, mock_repo, _ = client_with_mocks
        mock_repo.list_stories = AsyncMock(return_value=([], 0))

        response = client.get("/stories/")

        assert response.status_code == 200
        data = response.json()
        assert data["stories"] == []
        assert data["total"] == 0

    def test_list_stories_pagination(self, client_with_mocks):
        """Pagination parameters should be passed to repository."""
        client, mock_repo, _ = client_with_mocks
        mock_repo.list_stories = AsyncMock(return_value=([], 0))

        response = client.get("/stories/?limit=10&offset=20")

        assert response.status_code == 200
        mock_repo.list_stories.assert_called_once_with(
            limit=10, offset=20, status=None
        )

    def test_list_stories_status_filter(self, client_with_mocks):
        """Status filter should be passed to repository."""
        client, mock_repo, _ = client_with_mocks
        mock_repo.list_stories = AsyncMock(return_value=([], 0))

        response = client.get("/stories/?status=completed")

        assert response.status_code == 200
        mock_repo.list_stories.assert_called_once_with(
            limit=20, offset=0, status="completed"
        )


class TestGetStory:
    """Tests for GET /stories/{id} endpoint."""

    def test_get_story_not_found(self, client_with_mocks):
        """Non-existent story should return 404."""
        client, mock_repo, _ = client_with_mocks
        mock_repo.get_story = AsyncMock(return_value=None)

        response = client.get("/stories/nonexistent-id")

        assert response.status_code == 404

    def test_get_story_returns_story(self, client_with_mocks):
        """Existing story should be returned."""
        client, mock_repo, _ = client_with_mocks

        from backend.api.models.enums import GenerationType, JobStatus
        from backend.api.models.responses import StoryResponse

        mock_story = StoryResponse(
            id="test-id",
            status=JobStatus.COMPLETED,
            goal="teach about sharing",
            target_age_range="4-7",
            generation_type=GenerationType.STANDARD,
            created_at=datetime.utcnow(),
            title="The Sharing Tree",
            word_count=500,
            page_count=15,
        )
        mock_repo.get_story = AsyncMock(return_value=mock_story)

        response = client.get("/stories/test-id")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-id"
        assert data["title"] == "The Sharing Tree"


class TestDeleteStory:
    """Tests for DELETE /stories/{id} endpoint."""

    def test_delete_story_not_found(self, client_with_mocks):
        """Deleting non-existent story should return 404."""
        client, mock_repo, _ = client_with_mocks
        mock_repo.delete_story = AsyncMock(return_value=False)

        response = client.delete("/stories/nonexistent-id")

        assert response.status_code == 404

    def test_delete_story_success(self, client_with_mocks):
        """Successful deletion should return 204."""
        client, mock_repo, _ = client_with_mocks
        mock_repo.delete_story = AsyncMock(return_value=True)

        response = client.delete("/stories/test-id")

        assert response.status_code == 204


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_returns_healthy(self, client_with_mocks):
        """Health endpoint should return healthy status."""
        client, _, _ = client_with_mocks

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
