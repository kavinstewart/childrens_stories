"""Unit tests for spread regeneration service logic."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
import tempfile

import pytest


TEST_STORY_ID = "12345678-1234-5678-1234-567812345678"
TEST_JOB_ID = "regen123"


def create_mock_pool_and_conn():
    """Create a properly mocked asyncpg pool and connection."""
    mock_conn = AsyncMock()
    mock_pool = MagicMock()

    # Create an async context manager for acquire()
    @asynccontextmanager
    async def mock_acquire():
        yield mock_conn

    mock_pool.acquire = mock_acquire
    mock_pool.close = AsyncMock()

    return mock_pool, mock_conn


def create_mock_story():
    """Create a mock story object."""
    mock_story = MagicMock()
    mock_story.outline = MagicMock()
    mock_story.outline.title = "Test Story"
    mock_story.outline.characters = "Fox"
    mock_story.outline.setting = "Forest"
    mock_story.outline.plot_summary = "A fox learns to share"
    mock_story.outline.spread_count = 12
    mock_story.character_references = []
    return mock_story


class TestRegenerateSpreadService:
    """Tests for regenerate_spread function."""

    @pytest.mark.asyncio
    async def test_regenerate_spread_updates_job_status_to_running(self):
        """Regeneration updates job status to running at start."""
        from backend.api.services.spread_regeneration import regenerate_spread

        mock_pool, mock_conn = create_mock_pool_and_conn()
        mock_story = create_mock_story()

        with patch("backend.api.services.spread_regeneration.asyncpg") as mock_asyncpg, \
             patch("backend.api.services.spread_regeneration.StoryRepository") as mock_repo_class, \
             patch("backend.api.services.spread_regeneration.SpreadRegenJobRepository") as mock_regen_repo_class, \
             patch("backend.core.modules.spread_illustrator.SpreadIllustrator") as mock_illustrator_class, \
             patch("backend.api.services.spread_regeneration._load_character_refs") as mock_load_refs, \
             patch("backend.api.services.spread_regeneration._save_image_atomically") as mock_save:

            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_story = AsyncMock(return_value=mock_story)

            mock_regen_repo = AsyncMock()
            mock_regen_repo_class.return_value = mock_regen_repo
            mock_regen_repo.get_spread = AsyncMock(return_value={
                "spread_number": 3,
                "text": "The fox shared.",
                "word_count": 3,
                "illustration_prompt": "A fox sharing food",
            })

            mock_load_refs.return_value = None
            mock_save.return_value = None

            mock_illustrator = MagicMock()
            mock_illustrator.illustrate_spread.return_value = b"fake_image_bytes"
            mock_illustrator_class.return_value = mock_illustrator

            await regenerate_spread(TEST_JOB_ID, TEST_STORY_ID, 3)

            # Verify status was updated to running
            # update_status(job_id, status, started_at=...)
            calls = mock_regen_repo.update_status.call_args_list
            assert len(calls) >= 1
            first_call = calls[0]
            # First two args are positional: (job_id, status)
            assert first_call[0][1] == "running"
            assert first_call[1]["started_at"] is not None

    @pytest.mark.asyncio
    async def test_regenerate_spread_calls_illustrator_with_correct_params(self):
        """Regeneration calls SpreadIllustrator with correct spread data."""
        from backend.api.services.spread_regeneration import regenerate_spread

        mock_pool, mock_conn = create_mock_pool_and_conn()
        mock_story = create_mock_story()
        mock_story.outline.title = "Test"
        mock_story.outline.characters = ""
        mock_story.outline.setting = ""
        mock_story.outline.plot_summary = ""

        with patch("backend.api.services.spread_regeneration.asyncpg") as mock_asyncpg, \
             patch("backend.api.services.spread_regeneration.StoryRepository") as mock_repo_class, \
             patch("backend.api.services.spread_regeneration.SpreadRegenJobRepository") as mock_regen_repo_class, \
             patch("backend.core.modules.spread_illustrator.SpreadIllustrator") as mock_illustrator_class, \
             patch("backend.api.services.spread_regeneration._load_character_refs") as mock_load_refs, \
             patch("backend.api.services.spread_regeneration._save_image_atomically") as mock_save:

            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_story = AsyncMock(return_value=mock_story)

            mock_regen_repo = AsyncMock()
            mock_regen_repo_class.return_value = mock_regen_repo
            mock_regen_repo.get_spread = AsyncMock(return_value={
                "spread_number": 5,
                "text": "Test spread text",
                "word_count": 3,
                "illustration_prompt": "Test illustration prompt",
            })

            mock_load_refs.return_value = None
            mock_save.return_value = None

            mock_illustrator = MagicMock()
            mock_illustrator.illustrate_spread.return_value = b"image"
            mock_illustrator_class.return_value = mock_illustrator

            await regenerate_spread(TEST_JOB_ID, TEST_STORY_ID, 5)

            # Verify illustrator was called
            mock_illustrator.illustrate_spread.assert_called_once()
            call_kwargs = mock_illustrator.illustrate_spread.call_args[1]
            assert call_kwargs["spread"].spread_number == 5
            assert call_kwargs["spread"].text == "Test spread text"
            assert call_kwargs["spread"].illustration_prompt == "Test illustration prompt"

    @pytest.mark.asyncio
    async def test_regenerate_spread_updates_job_to_completed_on_success(self):
        """Successful regeneration updates job status to completed."""
        from backend.api.services.spread_regeneration import regenerate_spread

        mock_pool, mock_conn = create_mock_pool_and_conn()
        mock_story = create_mock_story()
        mock_story.outline.title = "Test"
        mock_story.outline.characters = ""
        mock_story.outline.setting = ""
        mock_story.outline.plot_summary = ""

        with patch("backend.api.services.spread_regeneration.asyncpg") as mock_asyncpg, \
             patch("backend.api.services.spread_regeneration.StoryRepository") as mock_repo_class, \
             patch("backend.api.services.spread_regeneration.SpreadRegenJobRepository") as mock_regen_repo_class, \
             patch("backend.core.modules.spread_illustrator.SpreadIllustrator") as mock_illustrator_class, \
             patch("backend.api.services.spread_regeneration._load_character_refs") as mock_load_refs, \
             patch("backend.api.services.spread_regeneration._save_image_atomically") as mock_save:

            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_story = AsyncMock(return_value=mock_story)

            mock_regen_repo = AsyncMock()
            mock_regen_repo_class.return_value = mock_regen_repo
            mock_regen_repo.get_spread = AsyncMock(return_value={
                "spread_number": 1,
                "text": "Text",
                "word_count": 1,
                "illustration_prompt": "Prompt",
            })

            mock_load_refs.return_value = None
            mock_save.return_value = None

            mock_illustrator = MagicMock()
            mock_illustrator.illustrate_spread.return_value = b"image"
            mock_illustrator_class.return_value = mock_illustrator

            await regenerate_spread(TEST_JOB_ID, TEST_STORY_ID, 1)

            # Verify status was updated to completed
            # update_status(job_id, status, completed_at=...)
            calls = mock_regen_repo.update_status.call_args_list
            last_call = calls[-1]
            # First two args are positional: (job_id, status)
            assert last_call[0][1] == "completed"
            assert last_call[1]["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_regenerate_spread_updates_job_to_failed_on_error(self):
        """Failed regeneration updates job status to failed with error message."""
        from backend.api.services.spread_regeneration import regenerate_spread

        mock_pool, mock_conn = create_mock_pool_and_conn()
        mock_story = create_mock_story()
        mock_story.outline.title = "Test"
        mock_story.outline.characters = ""
        mock_story.outline.setting = ""
        mock_story.outline.plot_summary = ""

        with patch("backend.api.services.spread_regeneration.asyncpg") as mock_asyncpg, \
             patch("backend.api.services.spread_regeneration.StoryRepository") as mock_repo_class, \
             patch("backend.api.services.spread_regeneration.SpreadRegenJobRepository") as mock_regen_repo_class, \
             patch("backend.core.modules.spread_illustrator.SpreadIllustrator") as mock_illustrator_class, \
             patch("backend.api.services.spread_regeneration._load_character_refs") as mock_load_refs:

            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_story = AsyncMock(return_value=mock_story)

            mock_regen_repo = AsyncMock()
            mock_regen_repo_class.return_value = mock_regen_repo
            mock_regen_repo.get_spread = AsyncMock(return_value={
                "spread_number": 1,
                "text": "Text",
                "word_count": 1,
                "illustration_prompt": "Prompt",
            })

            mock_load_refs.return_value = None

            # Make illustrator fail
            mock_illustrator = MagicMock()
            mock_illustrator.illustrate_spread.side_effect = RuntimeError("API Error")
            mock_illustrator_class.return_value = mock_illustrator

            with pytest.raises(RuntimeError):
                await regenerate_spread(TEST_JOB_ID, TEST_STORY_ID, 1)

            # Verify status was updated to failed
            # update_status(job_id, status, completed_at=..., error_message=...)
            calls = mock_regen_repo.update_status.call_args_list
            # Status is second positional arg
            failed_call = [c for c in calls if c[0][1] == "failed"]
            assert len(failed_call) == 1
            assert "API Error" in failed_call[0][1]["error_message"]

    @pytest.mark.asyncio
    async def test_regenerate_spread_raises_for_missing_story(self):
        """Regeneration raises ValueError for non-existent story."""
        from backend.api.services.spread_regeneration import regenerate_spread

        mock_pool, mock_conn = create_mock_pool_and_conn()

        with patch("backend.api.services.spread_regeneration.asyncpg") as mock_asyncpg, \
             patch("backend.api.services.spread_regeneration.StoryRepository") as mock_repo_class, \
             patch("backend.api.services.spread_regeneration.SpreadRegenJobRepository") as mock_regen_repo_class:

            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_story = AsyncMock(return_value=None)

            mock_regen_repo = AsyncMock()
            mock_regen_repo_class.return_value = mock_regen_repo

            with pytest.raises(ValueError, match="not found"):
                await regenerate_spread(TEST_JOB_ID, TEST_STORY_ID, 1)

    @pytest.mark.asyncio
    async def test_regenerate_spread_raises_for_missing_spread(self):
        """Regeneration raises ValueError for non-existent spread."""
        from backend.api.services.spread_regeneration import regenerate_spread

        mock_pool, mock_conn = create_mock_pool_and_conn()
        mock_story = create_mock_story()

        with patch("backend.api.services.spread_regeneration.asyncpg") as mock_asyncpg, \
             patch("backend.api.services.spread_regeneration.StoryRepository") as mock_repo_class, \
             patch("backend.api.services.spread_regeneration.SpreadRegenJobRepository") as mock_regen_repo_class:

            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_story = AsyncMock(return_value=mock_story)

            mock_regen_repo = AsyncMock()
            mock_regen_repo_class.return_value = mock_regen_repo
            mock_regen_repo.get_spread = AsyncMock(return_value=None)

            with pytest.raises(ValueError, match="Spread.*not found"):
                await regenerate_spread(TEST_JOB_ID, TEST_STORY_ID, 99)
