"""Unit tests for ARQ worker and story generation task."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock, call


class TestGenerateStoryTask:
    """Tests for the generate_story_task ARQ task."""

    @pytest.mark.asyncio
    async def test_task_calls_generate_story_with_correct_params(self):
        """Task should call generate_story with all provided parameters."""
        with patch("backend.worker.generate_story", new_callable=AsyncMock) as mock_gen:
            from backend.worker import generate_story_task

            mock_pool = MagicMock()
            ctx = {"job_id": "test-job-123", "pool": mock_pool}
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
                pool=mock_pool,
            )
            assert result["story_id"] == "story-uuid-456"
            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_task_uses_default_params_when_not_provided(self):
        """Task should use default parameters when not explicitly provided."""
        with patch("backend.worker.generate_story", new_callable=AsyncMock) as mock_gen:
            from backend.worker import generate_story_task

            mock_pool = MagicMock()
            ctx = {"job_id": "test-job", "pool": mock_pool}
            await generate_story_task(
                ctx,
                story_id="story-123",
                goal="test goal",
            )

            # Check defaults were used
            call_kwargs = mock_gen.call_args.kwargs
            assert call_kwargs["target_age_range"] == "4-7"
            assert call_kwargs["generation_type"] == "illustrated"
            assert call_kwargs["pool"] is mock_pool

    @pytest.mark.asyncio
    async def test_task_reraises_exceptions(self):
        """Task should re-raise exceptions so ARQ marks job as failed."""
        with patch("backend.worker.generate_story", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = ValueError("Generation failed")

            from backend.worker import generate_story_task

            mock_pool = MagicMock()
            ctx = {"job_id": "test-job", "pool": mock_pool}
            with pytest.raises(ValueError, match="Generation failed"):
                await generate_story_task(
                    ctx,
                    story_id="story-123",
                    goal="test goal",
                )

    @pytest.mark.asyncio
    async def test_task_fails_fast_when_pool_missing(self):
        """Task should raise RuntimeError immediately if pool not in context."""
        from backend.worker import generate_story_task

        ctx = {"job_id": "test-job"}  # No pool
        with pytest.raises(RuntimeError, match="Database pool not available"):
            await generate_story_task(
                ctx,
                story_id="story-123",
                goal="test goal",
            )

    @pytest.mark.asyncio
    async def test_task_handles_missing_job_id_in_context(self):
        """Task should handle missing job_id gracefully (pool is required)."""
        with patch("backend.worker.generate_story", new_callable=AsyncMock):
            from backend.worker import generate_story_task

            mock_pool = MagicMock()
            ctx = {"pool": mock_pool}  # No job_id but has pool
            result = await generate_story_task(
                ctx,
                story_id="story-123",
                goal="test goal",
            )

            assert result["status"] == "completed"


class TestRegenerateSpreadTask:
    """Tests for the regenerate_spread_task ARQ task."""

    @pytest.mark.asyncio
    async def test_task_calls_regenerate_spread_with_correct_params(self):
        """Task should call regenerate_spread with all provided parameters."""
        with patch("backend.worker.regenerate_spread", new_callable=AsyncMock) as mock_regen:
            from backend.worker import regenerate_spread_task

            mock_pool = MagicMock()
            ctx = {"job_id": "arq-job-123", "pool": mock_pool}
            result = await regenerate_spread_task(
                ctx,
                job_id="regen-job-456",
                story_id="story-uuid-789",
                spread_number=5,
                custom_prompt="A friendly fox in a meadow",
            )

            mock_regen.assert_called_once_with(
                job_id="regen-job-456",
                story_id="story-uuid-789",
                spread_number=5,
                custom_prompt="A friendly fox in a meadow",
                pool=mock_pool,
            )
            assert result["job_id"] == "regen-job-456"
            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_task_fails_fast_when_pool_missing(self):
        """Task should raise RuntimeError immediately if pool not in context."""
        from backend.worker import regenerate_spread_task

        ctx = {"job_id": "test-job"}  # No pool
        with pytest.raises(RuntimeError, match="Database pool not available"):
            await regenerate_spread_task(
                ctx,
                job_id="regen-123",
                story_id="story-123",
                spread_number=1,
            )

    @pytest.mark.asyncio
    async def test_task_reraises_exceptions(self):
        """Task should re-raise exceptions so ARQ marks job as failed."""
        with patch("backend.worker.regenerate_spread", new_callable=AsyncMock) as mock_regen:
            mock_regen.side_effect = ValueError("Story not found")

            from backend.worker import regenerate_spread_task

            mock_pool = MagicMock()
            ctx = {"job_id": "test-job", "pool": mock_pool}
            with pytest.raises(ValueError, match="Story not found"):
                await regenerate_spread_task(
                    ctx,
                    job_id="regen-123",
                    story_id="story-123",
                    spread_number=1,
                )


class TestWorkerPoolLifecycle:
    """Tests for worker startup/shutdown pool management."""

    @pytest.mark.asyncio
    async def test_startup_creates_pool_in_context(self):
        """startup() should create a database pool and store in ctx['pool']."""
        with patch("backend.worker.create_db_pool", new_callable=AsyncMock) as mock_create, \
             patch("backend.worker._cleanup_stale_redis_keys", new_callable=AsyncMock), \
             patch("backend.worker.StoryRepository") as mock_story_repo_cls, \
             patch("backend.worker.SpreadRegenJobRepository") as mock_regen_repo_cls:
            mock_pool = MagicMock()
            mock_pool.acquire = MagicMock(return_value=AsyncMock())
            mock_create.return_value = mock_pool

            # Configure mock repos
            mock_story_repo = AsyncMock()
            mock_story_repo.cleanup_stale_stories = AsyncMock(return_value=0)
            mock_story_repo_cls.return_value = mock_story_repo
            mock_regen_repo = AsyncMock()
            mock_regen_repo.cleanup_stale_jobs = AsyncMock(return_value=0)
            mock_regen_repo_cls.return_value = mock_regen_repo

            from backend.worker import startup

            ctx = {"redis": MagicMock()}
            await startup(ctx)

            mock_create.assert_called_once_with(min_size=3, max_size=8)
            assert ctx["pool"] is mock_pool

    @pytest.mark.asyncio
    async def test_startup_raises_if_pool_creation_fails(self):
        """startup() should propagate RuntimeError if DATABASE_URL not configured."""
        with patch("backend.worker.create_db_pool", new_callable=AsyncMock) as mock_create, \
             patch("backend.worker._cleanup_stale_redis_keys", new_callable=AsyncMock):
            mock_create.side_effect = RuntimeError("DATABASE_URL not configured")

            from backend.worker import startup

            ctx = {"redis": MagicMock()}
            with pytest.raises(RuntimeError, match="DATABASE_URL"):
                await startup(ctx)

    @pytest.mark.asyncio
    async def test_shutdown_closes_pool_with_error_handling(self):
        """shutdown() should close pool and handle errors gracefully."""
        from backend.worker import shutdown

        mock_pool = AsyncMock()
        ctx = {"pool": mock_pool}

        await shutdown(ctx)

        mock_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_handles_close_error(self):
        """shutdown() should not raise if pool.close() fails."""
        from backend.worker import shutdown

        mock_pool = AsyncMock()
        mock_pool.close.side_effect = Exception("Connection already closed")
        ctx = {"pool": mock_pool}

        # Should not raise
        await shutdown(ctx)

    @pytest.mark.asyncio
    async def test_shutdown_handles_missing_pool(self):
        """shutdown() should handle missing pool gracefully."""
        from backend.worker import shutdown

        ctx = {}  # No pool
        # Should not raise
        await shutdown(ctx)


class TestCleanupStaleJobsTask:
    """Tests for cleanup_stale_jobs_task using shared pool."""

    @pytest.mark.asyncio
    async def test_cleanup_uses_pool_from_context(self):
        """cleanup_stale_jobs_task should use ctx['pool'] instead of creating connection."""
        from backend.worker import cleanup_stale_jobs_task
        from contextlib import asynccontextmanager

        # Create mock pool with acquire context manager
        mock_conn = AsyncMock()
        mock_pool = MagicMock()

        @asynccontextmanager
        async def mock_acquire():
            yield mock_conn

        mock_pool.acquire = mock_acquire

        with patch("backend.worker.StoryRepository") as mock_story_repo_cls, \
             patch("backend.worker.SpreadRegenJobRepository") as mock_regen_repo_cls:
            mock_story_repo = AsyncMock()
            mock_story_repo.cleanup_stale_stories = AsyncMock(return_value=2)
            mock_story_repo_cls.return_value = mock_story_repo
            mock_regen_repo = AsyncMock()
            mock_regen_repo.cleanup_stale_jobs = AsyncMock(return_value=1)
            mock_regen_repo_cls.return_value = mock_regen_repo

            ctx = {"pool": mock_pool}
            result = await cleanup_stale_jobs_task(ctx)

            assert result["cleaned_stories"] == 2
            assert result["cleaned_spreads"] == 1
            # Repos should be instantiated with the connection from pool
            mock_story_repo_cls.assert_called_with(mock_conn)
            mock_regen_repo_cls.assert_called_with(mock_conn)

    @pytest.mark.asyncio
    async def test_cleanup_skips_if_pool_missing(self):
        """cleanup_stale_jobs_task should skip gracefully if pool not in context."""
        from backend.worker import cleanup_stale_jobs_task

        ctx = {}  # No pool
        result = await cleanup_stale_jobs_task(ctx)

        assert result["cleaned_stories"] == 0
        assert result["cleaned_spreads"] == 0


class TestWorkerSettings:
    """Tests for ARQ WorkerSettings configuration."""

    def test_worker_settings_has_generate_story_task(self):
        """WorkerSettings should register the generate_story_task function."""
        from backend.worker import WorkerSettings, generate_story_task

        assert generate_story_task in WorkerSettings.functions

    def test_worker_settings_has_regenerate_spread_task(self):
        """WorkerSettings should register the regenerate_spread_task function."""
        from backend.worker import WorkerSettings, regenerate_spread_task

        assert regenerate_spread_task in WorkerSettings.functions

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

    def test_worker_settings_retries_failed_jobs(self):
        """WorkerSettings should retry failed jobs as a safety net."""
        from backend.worker import WorkerSettings

        # Retry transient failures (503, timeouts, etc.)
        # Primary retry happens at @image_retry decorator level
        # ARQ retry is a safety net for errors outside image generation
        assert WorkerSettings.max_tries == 3

    def test_worker_settings_has_retry_delay(self):
        """WorkerSettings should have exponential backoff between retries."""
        from backend.worker import WorkerSettings

        # Should wait before retrying to avoid hammering overloaded services
        assert hasattr(WorkerSettings, "retry_delay")
        # Check it's a reasonable delay (not instant, not too long)
        # retry_delay should be a function or value representing backoff
        assert WorkerSettings.retry_delay is not None


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


class TestCleanupStaleRedisKeys:
    """Tests for _cleanup_stale_redis_keys function.

    CRITICAL: ARQ uses STRING type for all keys:
    - arq:job:* - serialized job data (psetex)
    - arq:in-progress:* - marker "1" with TTL (psetex)
    - arq:retry:* - retry count (incr/setex)
    - arq:result:* - serialized result (set)

    Only arq:queue is a zset. The cleanup function must NOT delete
    valid job/retry/result keys based on type checks.
    """

    @pytest.mark.asyncio
    async def test_cleanup_only_deletes_in_progress_keys(self):
        """Cleanup should only delete arq:in-progress:* keys for regular jobs."""
        from backend.worker import _cleanup_stale_redis_keys

        mock_redis = AsyncMock()
        mock_redis.keys = AsyncMock(return_value=[
            b"arq:in-progress:job123",
            b"arq:in-progress:job456",
        ])
        mock_redis.delete = AsyncMock()

        ctx = {"redis": mock_redis}
        await _cleanup_stale_redis_keys(ctx)

        # Should delete both in-progress keys
        assert mock_redis.delete.call_count == 2
        mock_redis.delete.assert_any_call(b"arq:in-progress:job123")
        mock_redis.delete.assert_any_call(b"arq:in-progress:job456")

    @pytest.mark.asyncio
    async def test_cleanup_skips_cron_in_progress_keys(self):
        """Cleanup should skip arq:in-progress:cron:* keys."""
        from backend.worker import _cleanup_stale_redis_keys

        mock_redis = AsyncMock()
        mock_redis.keys = AsyncMock(return_value=[
            b"arq:in-progress:job123",
            b"arq:in-progress:cron:cleanup_stale_jobs_task:123456",
            b"arq:in-progress:cron:some_other_cron:789",
        ])
        mock_redis.delete = AsyncMock()

        ctx = {"redis": mock_redis}
        await _cleanup_stale_redis_keys(ctx)

        # Should only delete the non-cron key
        mock_redis.delete.assert_called_once_with(b"arq:in-progress:job123")

    @pytest.mark.asyncio
    async def test_cleanup_does_not_touch_job_keys(self):
        """Cleanup must NOT delete arq:job:* keys - they contain valid job data."""
        from backend.worker import _cleanup_stale_redis_keys

        mock_redis = AsyncMock()
        # Only return in-progress keys from keys() call
        mock_redis.keys = AsyncMock(return_value=[])
        mock_redis.delete = AsyncMock()

        ctx = {"redis": mock_redis}
        await _cleanup_stale_redis_keys(ctx)

        # Should not call keys() for job keys at all
        # The function should only query arq:in-progress:*
        calls = [c for c in mock_redis.keys.call_args_list]
        for c in calls:
            pattern = c[0][0] if c[0] else c[1].get("pattern", "")
            pattern_str = pattern.decode() if isinstance(pattern, bytes) else str(pattern)
            assert "arq:job:" not in pattern_str

    @pytest.mark.asyncio
    async def test_cleanup_does_not_touch_retry_keys(self):
        """Cleanup must NOT delete arq:retry:* keys - they track retry counts."""
        from backend.worker import _cleanup_stale_redis_keys

        mock_redis = AsyncMock()
        mock_redis.keys = AsyncMock(return_value=[])
        mock_redis.delete = AsyncMock()

        ctx = {"redis": mock_redis}
        await _cleanup_stale_redis_keys(ctx)

        # Should not query or delete retry keys
        calls = [c for c in mock_redis.keys.call_args_list]
        for c in calls:
            pattern = c[0][0] if c[0] else c[1].get("pattern", "")
            pattern_str = pattern.decode() if isinstance(pattern, bytes) else str(pattern)
            assert "arq:retry:" not in pattern_str

    @pytest.mark.asyncio
    async def test_cleanup_does_not_touch_result_keys(self):
        """Cleanup must NOT delete arq:result:* keys - they contain job results."""
        from backend.worker import _cleanup_stale_redis_keys

        mock_redis = AsyncMock()
        mock_redis.keys = AsyncMock(return_value=[])
        mock_redis.delete = AsyncMock()

        ctx = {"redis": mock_redis}
        await _cleanup_stale_redis_keys(ctx)

        # Should not query or delete result keys
        calls = [c for c in mock_redis.keys.call_args_list]
        for c in calls:
            pattern = c[0][0] if c[0] else c[1].get("pattern", "")
            pattern_str = pattern.decode() if isinstance(pattern, bytes) else str(pattern)
            assert "arq:result:" not in pattern_str

    @pytest.mark.asyncio
    async def test_cleanup_handles_missing_redis_context(self):
        """Cleanup should handle missing redis connection gracefully."""
        from backend.worker import _cleanup_stale_redis_keys

        ctx = {}  # No redis
        # Should not raise
        await _cleanup_stale_redis_keys(ctx)

    @pytest.mark.asyncio
    async def test_cleanup_handles_redis_errors(self):
        """Cleanup should handle Redis errors gracefully."""
        from backend.worker import _cleanup_stale_redis_keys

        mock_redis = AsyncMock()
        mock_redis.keys = AsyncMock(side_effect=Exception("Redis connection lost"))

        ctx = {"redis": mock_redis}
        # Should not raise, just log error
        await _cleanup_stale_redis_keys(ctx)
