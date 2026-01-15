"""Integration tests for story API endpoints."""

from unittest.mock import AsyncMock
from datetime import datetime
from uuid import UUID

# Valid test UUIDs for mocking
TEST_UUID = UUID("12345678-1234-5678-1234-567812345678")
TEST_UUID_STR = "12345678-1234-5678-1234-567812345678"


class TestCreateStory:
    """Tests for POST /stories endpoint."""

    def test_create_story_returns_202_with_job_id(self, client_with_mocks):
        """Creating a story should return 202 Accepted with a job ID."""
        client, mock_repo, _, mock_service = client_with_mocks
        mock_service.create_story_job = AsyncMock(return_value=TEST_UUID_STR)

        response = client.post(
            "/stories/",
            json={"goal": "teach about sharing"},
        )

        assert response.status_code == 202
        data = response.json()
        assert data["id"] == TEST_UUID_STR
        assert data["status"] == "pending"

    def test_create_story_validates_goal_min_length(self, client_with_mocks):
        """Goal must be at least 3 characters."""
        client, _, _, _ = client_with_mocks

        response = client.post(
            "/stories/",
            json={"goal": "ab"},  # Too short
        )

        assert response.status_code == 422

    def test_create_story_accepts_all_generation_types(self, client_with_mocks):
        """All three generation types should be accepted."""
        client, mock_repo, _, mock_service = client_with_mocks
        mock_service.create_story_job = AsyncMock(return_value=TEST_UUID_STR)

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
        client, mock_repo, _, _ = client_with_mocks
        mock_repo.list_stories = AsyncMock(return_value=([], 0))

        response = client.get("/stories/")

        assert response.status_code == 200
        data = response.json()
        assert data["stories"] == []
        assert data["total"] == 0

    def test_list_stories_pagination(self, client_with_mocks):
        """Pagination parameters should be passed to repository."""
        client, mock_repo, _, _ = client_with_mocks
        mock_repo.list_stories = AsyncMock(return_value=([], 0))

        response = client.get("/stories/?limit=10&offset=20")

        assert response.status_code == 200
        # API defaults to completed status when not specified
        mock_repo.list_stories.assert_called_once_with(
            limit=10, offset=20, status="completed"
        )

    def test_list_stories_status_filter(self, client_with_mocks):
        """Status filter should be passed to repository."""
        client, mock_repo, _, _ = client_with_mocks
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
        client, mock_repo, _, _ = client_with_mocks
        mock_repo.get_story = AsyncMock(return_value=None)

        response = client.get("/stories/nonexistent-id")

        assert response.status_code == 404

    def test_get_story_returns_story(self, client_with_mocks):
        """Existing story should be returned."""
        client, mock_repo, _, _ = client_with_mocks

        from backend.api.models.enums import GenerationType, JobStatus
        from backend.api.models.responses import StoryResponse

        mock_story = StoryResponse(
            id=TEST_UUID,
            status=JobStatus.COMPLETED,
            goal="teach about sharing",
            target_age_range="4-7",
            generation_type=GenerationType.STANDARD,
            created_at=datetime.utcnow(),
            title="The Sharing Tree",
            word_count=500,
            spread_count=12,
        )
        mock_repo.get_story = AsyncMock(return_value=mock_story)

        response = client.get(f"/stories/{TEST_UUID_STR}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == TEST_UUID_STR
        assert data["title"] == "The Sharing Tree"


class TestDeleteStory:
    """Tests for DELETE /stories/{id} endpoint."""

    def test_delete_story_not_found(self, client_with_mocks):
        """Deleting non-existent story should return 404."""
        client, mock_repo, _, _ = client_with_mocks
        mock_repo.delete_story = AsyncMock(return_value=False)

        response = client.delete("/stories/nonexistent-id")

        assert response.status_code == 404

    def test_delete_story_success(self, client_with_mocks):
        """Successful deletion should return 204."""
        client, mock_repo, _, _ = client_with_mocks
        mock_repo.delete_story = AsyncMock(return_value=True)

        response = client.delete("/stories/test-id")

        assert response.status_code == 204


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_returns_healthy(self, client_with_mocks):
        """Health endpoint should return healthy status."""
        client, _, _, _ = client_with_mocks

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestDeprecatedEndpointsRemoved:
    """Tests to verify deprecated endpoints have been removed."""

    def test_page_image_endpoint_not_found(self, client_with_mocks):
        """Deprecated /pages/{page_number}/image endpoint should return 404."""
        client, _, _, _ = client_with_mocks

        response = client.get("/stories/test-id/pages/1/image")

        # Should be 404 (not found) since the endpoint was removed
        # If endpoint existed, it would return 404 for missing file, not route
        assert response.status_code == 404
        # The detail should indicate route not found, not file not found
        assert "pages" not in response.json().get("detail", "").lower() or \
               "not found" in response.json().get("detail", "").lower()


class TestRecommendations:
    """Tests for GET /stories/{id}/recommendations endpoint."""

    def test_recommendations_default_limit_is_3(self, client_with_mocks):
        """Default limit should be 3, not 4."""
        client, mock_repo, _, _ = client_with_mocks
        mock_repo.get_recommendations = AsyncMock(return_value=[])

        response = client.get("/stories/test-story-id/recommendations")

        assert response.status_code == 200
        # Verify the repository was called with limit=3 as default
        mock_repo.get_recommendations.assert_called_once_with(
            exclude_story_id="test-story-id",
            limit=3,
        )

    def test_recommendations_returns_list(self, client_with_mocks):
        """Recommendations endpoint should return a list of recommendations."""
        client, mock_repo, _, _ = client_with_mocks

        from backend.api.models.responses import StoryRecommendationItem
        from uuid import UUID

        mock_recommendations = [
            StoryRecommendationItem(
                id=UUID("11111111-1111-1111-1111-111111111111"),
                title="Story One",
                goal="teach about sharing",
                cover_url="/stories/11111111-1111-1111-1111-111111111111/spreads/1/image",
                is_illustrated=True,
            ),
            StoryRecommendationItem(
                id=UUID("22222222-2222-2222-2222-222222222222"),
                title="Story Two",
                goal="teach about kindness",
                cover_url="/stories/22222222-2222-2222-2222-222222222222/spreads/1/image",
                is_illustrated=False,
            ),
        ]
        mock_repo.get_recommendations = AsyncMock(return_value=mock_recommendations)

        response = client.get("/stories/test-story-id/recommendations")

        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert len(data["recommendations"]) == 2

    def test_recommendations_custom_limit(self, client_with_mocks):
        """Custom limit should be passed to repository."""
        client, mock_repo, _, _ = client_with_mocks
        mock_repo.get_recommendations = AsyncMock(return_value=[])

        response = client.get("/stories/test-story-id/recommendations?limit=5")

        assert response.status_code == 200
        mock_repo.get_recommendations.assert_called_once_with(
            exclude_story_id="test-story-id",
            limit=5,
        )


class TestStoryResponseShape:
    """Tests to verify API response shape after cleanup."""

    def test_story_response_uses_spread_count_not_page_count(self, client_with_mocks):
        """Story response should use spread_count, not page_count."""
        client, mock_repo, _, _ = client_with_mocks

        from backend.api.models.enums import GenerationType, JobStatus
        from backend.api.models.responses import StoryResponse

        mock_story = StoryResponse(
            id=TEST_UUID,
            status=JobStatus.COMPLETED,
            goal="teach about sharing",
            target_age_range="4-7",
            generation_type=GenerationType.STANDARD,
            spread_count=12,
        )
        mock_repo.get_story = AsyncMock(return_value=mock_story)

        response = client.get(f"/stories/{TEST_UUID_STR}")

        assert response.status_code == 200
        data = response.json()
        assert "spread_count" in data
        assert data["spread_count"] == 12
        # page_count should not exist (removed backwards compat alias)
        assert "page_count" not in data

    def test_story_response_uses_spreads_not_pages(self, client_with_mocks):
        """Story response should use spreads, not pages."""
        client, mock_repo, _, _ = client_with_mocks

        from backend.api.models.enums import GenerationType, JobStatus
        from backend.api.models.responses import StoryResponse, StorySpreadResponse

        mock_story = StoryResponse(
            id=TEST_UUID,
            status=JobStatus.COMPLETED,
            goal="teach about sharing",
            target_age_range="4-7",
            generation_type=GenerationType.STANDARD,
            spreads=[
                StorySpreadResponse(
                    spread_number=1,
                    text="Once upon a time...",
                    word_count=4,
                    was_revised=False,
                ),
            ],
        )
        mock_repo.get_story = AsyncMock(return_value=mock_story)

        response = client.get(f"/stories/{TEST_UUID_STR}")

        assert response.status_code == 200
        data = response.json()
        assert "spreads" in data
        assert len(data["spreads"]) == 1
        assert data["spreads"][0]["spread_number"] == 1
        # pages should not exist (removed backwards compat alias)
        assert "pages" not in data
