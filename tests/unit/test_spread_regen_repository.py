"""Unit tests for spread regeneration repository methods."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from backend.api.database.repository import StoryRepository


TEST_STORY_ID = "12345678-1234-5678-1234-567812345678"
TEST_JOB_ID = "regen123"


@pytest.fixture
def mock_connection():
    """Create a mock asyncpg connection."""
    conn = MagicMock()
    conn.execute = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    return conn


@pytest.fixture
def repository(mock_connection):
    """Create a StoryRepository with mock connection."""
    return StoryRepository(mock_connection)


class TestCreateSpreadRegenJob:
    """Tests for create_spread_regen_job method."""

    @pytest.mark.asyncio
    async def test_creates_job_with_correct_fields(self, repository, mock_connection):
        """Creates job with correct fields (job_id, story_id, spread_number, status='pending')."""
        await repository.create_spread_regen_job(
            job_id=TEST_JOB_ID,
            story_id=TEST_STORY_ID,
            spread_number=3,
        )

        mock_connection.execute.assert_called_once()
        call_args = mock_connection.execute.call_args
        sql = call_args[0][0]

        assert "INSERT INTO spread_regen_jobs" in sql
        assert "'pending'" in sql
        assert call_args[0][1] == TEST_JOB_ID
        assert call_args[0][2] == TEST_STORY_ID
        assert call_args[0][3] == 3


class TestGetSpreadRegenJob:
    """Tests for get_spread_regen_job method."""

    @pytest.mark.asyncio
    async def test_returns_job_when_found(self, repository, mock_connection):
        """Returns job dict when found."""
        mock_row = MagicMock()
        mock_row.__iter__ = lambda self: iter([
            ("id", TEST_JOB_ID),
            ("story_id", TEST_STORY_ID),
            ("spread_number", 3),
            ("status", "pending"),
        ])
        mock_row.keys = lambda: ["id", "story_id", "spread_number", "status"]
        mock_row.__getitem__ = lambda self, key: {
            "id": TEST_JOB_ID,
            "story_id": TEST_STORY_ID,
            "spread_number": 3,
            "status": "pending",
        }[key]
        mock_connection.fetchrow = AsyncMock(return_value=mock_row)

        result = await repository.get_spread_regen_job(TEST_JOB_ID)

        assert result is not None
        mock_connection.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, repository, mock_connection):
        """Returns None for non-existent job_id."""
        mock_connection.fetchrow = AsyncMock(return_value=None)

        result = await repository.get_spread_regen_job("nonexistent")

        assert result is None


class TestGetActiveSpreadRegenJob:
    """Tests for get_active_spread_regen_job method."""

    @pytest.mark.asyncio
    async def test_returns_active_job(self, repository, mock_connection):
        """Returns active job when one exists."""
        mock_row = MagicMock()
        mock_connection.fetchrow = AsyncMock(return_value=mock_row)

        result = await repository.get_active_spread_regen_job(TEST_STORY_ID, 3)

        assert result is not None
        call_args = mock_connection.fetchrow.call_args
        sql = call_args[0][0]
        assert "pending" in sql and "running" in sql

    @pytest.mark.asyncio
    async def test_returns_none_when_no_active_job(self, repository, mock_connection):
        """Returns None when no active job exists."""
        mock_connection.fetchrow = AsyncMock(return_value=None)

        result = await repository.get_active_spread_regen_job(TEST_STORY_ID, 3)

        assert result is None


class TestUpdateSpreadRegenStatus:
    """Tests for update_spread_regen_status method."""

    @pytest.mark.asyncio
    async def test_updates_status_to_running(self, repository, mock_connection):
        """Updates status from 'pending' to 'running' with started_at."""
        now = datetime.now(timezone.utc)

        await repository.update_spread_regen_status(
            job_id=TEST_JOB_ID,
            status="running",
            started_at=now,
        )

        mock_connection.execute.assert_called_once()
        call_args = mock_connection.execute.call_args
        assert call_args[0][1] == TEST_JOB_ID
        assert call_args[0][2] == "running"
        assert call_args[0][3] == now

    @pytest.mark.asyncio
    async def test_updates_status_to_completed(self, repository, mock_connection):
        """Updates status to 'completed' with completed_at."""
        now = datetime.now(timezone.utc)

        await repository.update_spread_regen_status(
            job_id=TEST_JOB_ID,
            status="completed",
            completed_at=now,
        )

        mock_connection.execute.assert_called_once()
        call_args = mock_connection.execute.call_args
        assert call_args[0][2] == "completed"
        assert call_args[0][4] == now

    @pytest.mark.asyncio
    async def test_updates_status_to_failed_with_error(self, repository, mock_connection):
        """Updates status to 'failed' with error_message."""
        now = datetime.now(timezone.utc)

        await repository.update_spread_regen_status(
            job_id=TEST_JOB_ID,
            status="failed",
            completed_at=now,
            error_message="Image generation failed",
        )

        mock_connection.execute.assert_called_once()
        call_args = mock_connection.execute.call_args
        assert call_args[0][2] == "failed"
        assert call_args[0][5] == "Image generation failed"


class TestUpdateSpreadRegenProgress:
    """Tests for update_spread_regen_progress method."""

    @pytest.mark.asyncio
    async def test_updates_progress_json(self, repository, mock_connection):
        """Updates progress JSON field."""
        progress = '{"stage": "generating", "percent": 50}'

        await repository.update_spread_regen_progress(TEST_JOB_ID, progress)

        mock_connection.execute.assert_called_once()
        call_args = mock_connection.execute.call_args
        assert call_args[0][1] == TEST_JOB_ID
        assert call_args[0][2] == progress


class TestSaveRegeneratedSpread:
    """Tests for save_regenerated_spread method."""

    @pytest.mark.asyncio
    async def test_updates_illustration_path_and_timestamp(self, repository, mock_connection):
        """Updates illustration_path and sets illustration_updated_at."""
        path = "/data/stories/test/images/spread_03.png"

        await repository.save_regenerated_spread(
            story_id=TEST_STORY_ID,
            spread_number=3,
            illustration_path=path,
        )

        mock_connection.execute.assert_called_once()
        call_args = mock_connection.execute.call_args
        sql = call_args[0][0]

        assert "illustration_path" in sql
        assert "illustration_updated_at" in sql
        assert call_args[0][1] == TEST_STORY_ID
        assert call_args[0][2] == 3
        assert call_args[0][3] == path
        # Timestamp should be set (4th argument)
        assert call_args[0][4] is not None


class TestGetSpread:
    """Tests for get_spread method."""

    @pytest.mark.asyncio
    async def test_returns_spread_when_found(self, repository, mock_connection):
        """Returns spread dict when found."""
        mock_row = MagicMock()
        mock_connection.fetchrow = AsyncMock(return_value=mock_row)

        result = await repository.get_spread(TEST_STORY_ID, 3)

        assert result is not None
        mock_connection.fetchrow.assert_called_once()
        call_args = mock_connection.fetchrow.call_args
        assert call_args[0][1] == TEST_STORY_ID
        assert call_args[0][2] == 3

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, repository, mock_connection):
        """Returns None for non-existent spread."""
        mock_connection.fetchrow = AsyncMock(return_value=None)

        result = await repository.get_spread(TEST_STORY_ID, 99)

        assert result is None
