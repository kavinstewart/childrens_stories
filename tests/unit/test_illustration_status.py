"""Tests for illustration_status field in StorySpreadResponse."""

import pytest
from datetime import datetime, timezone
from uuid import UUID

from backend.api.models.responses import (
    StorySpreadResponse,
    StoryResponse,
    JobStatus,
)
from backend.api.models.enums import GenerationType


class TestStorySpreadResponseIllustrationStatus:
    """Tests for illustration_status field on StorySpreadResponse."""

    def test_illustration_status_complete_when_url_present(self):
        """Status should be 'complete' when illustration_url is present."""
        spread = StorySpreadResponse(
            spread_number=1,
            text="Test text",
            word_count=10,
            illustration_url="/stories/123/spreads/1/image",
            illustration_status="complete",
        )
        assert spread.illustration_status == "complete"

    def test_illustration_status_failed_when_url_none(self):
        """Status should be 'failed' when illustration_url is None and story completed."""
        spread = StorySpreadResponse(
            spread_number=1,
            text="Test text",
            word_count=10,
            illustration_url=None,
            illustration_status="failed",
        )
        assert spread.illustration_status == "failed"

    def test_illustration_status_pending_when_url_none_and_story_generating(self):
        """Status should be 'pending' when illustration_url is None and story still generating."""
        spread = StorySpreadResponse(
            spread_number=1,
            text="Test text",
            word_count=10,
            illustration_url=None,
            illustration_status="pending",
        )
        assert spread.illustration_status == "pending"

    def test_illustration_status_is_required_field(self):
        """illustration_status should be a required field with a default."""
        # With illustration_url present, default should be 'complete'
        spread = StorySpreadResponse(
            spread_number=1,
            text="Test text",
            word_count=10,
            illustration_url="/stories/123/spreads/1/image",
        )
        assert spread.illustration_status == "complete"

        # With illustration_url None, default should be 'pending' (safest default)
        spread_no_url = StorySpreadResponse(
            spread_number=1,
            text="Test text",
            word_count=10,
            illustration_url=None,
        )
        assert spread_no_url.illustration_status == "pending"


class TestRepositoryBuildsCorrectIllustrationStatus:
    """Tests that repository correctly sets illustration_status based on story state."""

    @pytest.fixture
    def mock_spread_record(self):
        """Create a mock spread record as returned by DB."""
        return {
            "spread_number": 1,
            "text": "Test spread text",
            "word_count": 15,
            "was_revised": False,
            "page_turn_note": None,
            "illustration_prompt": "A test illustration",
            "illustration_path": None,  # No illustration
            "illustration_updated_at": None,
        }

    @pytest.fixture
    def mock_spread_record_with_illustration(self):
        """Create a mock spread record with illustration."""
        return {
            "spread_number": 1,
            "text": "Test spread text",
            "word_count": 15,
            "was_revised": False,
            "page_turn_note": None,
            "illustration_prompt": "A test illustration",
            "illustration_path": "/path/to/image.png",
            "illustration_updated_at": datetime.now(timezone.utc),
        }

    def test_spread_with_illustration_has_complete_status(
        self, mock_spread_record_with_illustration
    ):
        """Spread with illustration_path should have status 'complete'."""
        from backend.api.database.repository import StoryRepository
        from unittest.mock import MagicMock

        repo = StoryRepository(MagicMock())
        spreads = repo._build_spread_responses(
            story_id="test-id",
            spreads=[mock_spread_record_with_illustration],
            metadata=None,
            story_status="completed",
        )

        assert len(spreads) == 1
        assert spreads[0].illustration_status == "complete"
        assert spreads[0].illustration_url is not None

    def test_spread_without_illustration_completed_story_has_failed_status(
        self, mock_spread_record
    ):
        """Spread without illustration in completed story should have status 'failed'."""
        from backend.api.database.repository import StoryRepository
        from unittest.mock import MagicMock

        repo = StoryRepository(MagicMock())
        spreads = repo._build_spread_responses(
            story_id="test-id",
            spreads=[mock_spread_record],
            metadata=None,
            story_status="completed",
        )

        assert len(spreads) == 1
        assert spreads[0].illustration_status == "failed"
        assert spreads[0].illustration_url is None

    def test_spread_without_illustration_running_story_has_pending_status(
        self, mock_spread_record
    ):
        """Spread without illustration in running story should have status 'pending'."""
        from backend.api.database.repository import StoryRepository
        from unittest.mock import MagicMock

        repo = StoryRepository(MagicMock())
        spreads = repo._build_spread_responses(
            story_id="test-id",
            spreads=[mock_spread_record],
            metadata=None,
            story_status="running",
        )

        assert len(spreads) == 1
        assert spreads[0].illustration_status == "pending"
        assert spreads[0].illustration_url is None

    def test_spread_without_illustration_pending_story_has_pending_status(
        self, mock_spread_record
    ):
        """Spread without illustration in pending story should have status 'pending'."""
        from backend.api.database.repository import StoryRepository
        from unittest.mock import MagicMock

        repo = StoryRepository(MagicMock())
        spreads = repo._build_spread_responses(
            story_id="test-id",
            spreads=[mock_spread_record],
            metadata=None,
            story_status="pending",
        )

        assert len(spreads) == 1
        assert spreads[0].illustration_status == "pending"

    def test_spread_without_illustration_failed_story_has_failed_status(
        self, mock_spread_record
    ):
        """Spread without illustration in failed story should have status 'failed'."""
        from backend.api.database.repository import StoryRepository
        from unittest.mock import MagicMock

        repo = StoryRepository(MagicMock())
        spreads = repo._build_spread_responses(
            story_id="test-id",
            spreads=[mock_spread_record],
            metadata=None,
            story_status="failed",
        )

        assert len(spreads) == 1
        assert spreads[0].illustration_status == "failed"
