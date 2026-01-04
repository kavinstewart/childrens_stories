"""Unit tests for ARQ worker and story generation task."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestGenerateStoryTask:
    """Tests for the generate_story_task ARQ task."""

    @pytest.mark.asyncio
    async def test_task_calls_generate_story_with_correct_params(self):
        """Task should call generate_story with all provided parameters."""
        with patch("backend.worker.generate_story", new_callable=AsyncMock) as mock_gen:
            from backend.worker import generate_story_task

            ctx = {"job_id": "test-job-123"}
            result = await generate_story_task(
                ctx,
                story_id="story-uuid-456",
                goal="teach about sharing",
                target_age_range="4-7",
                generation_type="illustrated",
            )

            mock_gen.assert_called_once_with(
                story_id="story-uuid-456",
                goal="teach about sharing",
                target_age_range="4-7",
                generation_type="illustrated",
            )
            assert result["story_id"] == "story-uuid-456"
            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_task_uses_default_params_when_not_provided(self):
        """Task should use default parameters when not explicitly provided."""
        with patch("backend.worker.generate_story", new_callable=AsyncMock) as mock_gen:
            from backend.worker import generate_story_task

            ctx = {"job_id": "test-job"}
            await generate_story_task(
                ctx,
                story_id="story-123",
                goal="test goal",
            )

            # Check defaults were used
            call_kwargs = mock_gen.call_args.kwargs
            assert call_kwargs["target_age_range"] == "4-7"
            assert call_kwargs["generation_type"] == "illustrated"

    @pytest.mark.asyncio
    async def test_task_reraises_exceptions(self):
        """Task should re-raise exceptions so ARQ marks job as failed."""
        with patch("backend.worker.generate_story", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = ValueError("Generation failed")

            from backend.worker import generate_story_task

            ctx = {"job_id": "test-job"}
            with pytest.raises(ValueError, match="Generation failed"):
                await generate_story_task(
                    ctx,
                    story_id="story-123",
                    goal="test goal",
                )

    @pytest.mark.asyncio
    async def test_task_handles_missing_job_id_in_context(self):
        """Task should handle missing job_id gracefully."""
        with patch("backend.worker.generate_story", new_callable=AsyncMock):
            from backend.worker import generate_story_task

            ctx = {}  # No job_id
            result = await generate_story_task(
                ctx,
                story_id="story-123",
                goal="test goal",
            )

            assert result["status"] == "completed"


class TestWorkerSettings:
    """Tests for ARQ WorkerSettings configuration."""

    def test_worker_settings_has_generate_story_task(self):
        """WorkerSettings should register the generate_story_task function."""
        from backend.worker import WorkerSettings, generate_story_task

        assert generate_story_task in WorkerSettings.functions

    def test_worker_settings_has_lifecycle_hooks(self):
        """WorkerSettings should have startup and shutdown hooks."""
        from backend.worker import WorkerSettings

        assert WorkerSettings.on_startup is not None
        assert WorkerSettings.on_shutdown is not None

    def test_worker_settings_limits_concurrent_jobs(self):
        """WorkerSettings should limit concurrent jobs for resource-intensive work."""
        from backend.worker import WorkerSettings

        assert WorkerSettings.max_jobs <= 3  # Should be low

    def test_worker_settings_has_reasonable_timeout(self):
        """WorkerSettings should have a reasonable job timeout."""
        from backend.worker import WorkerSettings

        # Story generation can take several minutes
        assert WorkerSettings.job_timeout >= 300  # At least 5 minutes

    def test_worker_settings_no_auto_retry(self):
        """WorkerSettings should not auto-retry failed jobs."""
        from backend.worker import WorkerSettings

        # Failed stories are marked in DB, don't want duplicate attempts
        assert WorkerSettings.max_tries == 1


class TestArqPool:
    """Tests for ARQ pool management."""

    def test_get_pool_raises_when_not_initialized(self):
        """get_pool should raise RuntimeError when pool not set."""
        from backend.api import arq_pool

        # Save current state
        original_pool = arq_pool._pool
        arq_pool._pool = None

        try:
            with pytest.raises(RuntimeError, match="not initialized"):
                arq_pool.get_pool()
        finally:
            # Restore state
            arq_pool._pool = original_pool

    def test_set_pool_stores_pool(self):
        """set_pool should store the pool for later retrieval."""
        from backend.api import arq_pool

        # Save current state
        original_pool = arq_pool._pool

        try:
            mock_pool = MagicMock()
            arq_pool.set_pool(mock_pool)
            assert arq_pool.get_pool() is mock_pool
        finally:
            # Restore state
            arq_pool._pool = original_pool

    @pytest.mark.asyncio
    async def test_close_pool_closes_and_clears(self):
        """close_pool should close the pool and clear the reference."""
        from backend.api import arq_pool

        # Save current state
        original_pool = arq_pool._pool

        try:
            mock_pool = MagicMock()
            mock_pool.aclose = AsyncMock()
            arq_pool.set_pool(mock_pool)

            await arq_pool.close_pool()

            mock_pool.aclose.assert_called_once()
            assert arq_pool._pool is None
        finally:
            # Restore state
            arq_pool._pool = original_pool
