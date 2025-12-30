"""Integration tests for ARQ story generation flow.

These tests require:
- Running Redis server
- Running PostgreSQL database
- Environment variables configured

The actual LLM story generation is mocked to keep tests fast.
"""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from arq import create_pool
from arq.connections import RedisSettings


@pytest.fixture
def redis_available():
    """Check if Redis is available."""
    import redis
    try:
        r = redis.Redis()
        r.ping()
        return True
    except redis.ConnectionError:
        return False


@pytest.fixture
def skip_without_redis(redis_available):
    """Skip test if Redis is not available."""
    if not redis_available:
        pytest.skip("Redis not available")


class TestArqIntegration:
    """Integration tests for ARQ task queue."""

    @pytest.mark.asyncio
    async def test_can_connect_to_redis(self, skip_without_redis):
        """Verify we can connect to Redis via ARQ."""
        pool = await create_pool(RedisSettings())
        info = await pool.info()
        assert "redis_version" in info
        await pool.aclose()

    @pytest.mark.asyncio
    async def test_can_enqueue_job(self, skip_without_redis):
        """Verify we can enqueue a job to Redis."""
        pool = await create_pool(RedisSettings())

        try:
            # Enqueue a test job (won't be processed without worker)
            job = await pool.enqueue_job(
                "generate_story_task",
                story_id="test-integration-123",
                goal="test goal for integration",
            )

            assert job is not None
            assert job.job_id is not None

        finally:
            # Clean up - flush test data from Redis
            await pool.flushdb()
            await pool.aclose()

    @pytest.mark.asyncio
    async def test_worker_can_process_job(self, skip_without_redis):
        """Verify worker can pick up and process a job."""
        from backend.worker import generate_story_task

        # Mock the actual story generation
        with patch("backend.worker.generate_story", new_callable=AsyncMock) as mock_gen:
            ctx = {"job_id": "integration-test-job"}

            result = await generate_story_task(
                ctx,
                story_id="test-story-id",
                goal="A story about integration testing",
            )

            assert result["status"] == "completed"
            assert result["story_id"] == "test-story-id"
            mock_gen.assert_called_once()


class TestStoryServiceArqIntegration:
    """Integration tests for StoryService with ARQ."""

    @pytest.mark.asyncio
    async def test_create_story_job_enqueues_to_arq(self, skip_without_redis):
        """StoryService.create_story_job should enqueue to ARQ."""
        from backend.api.services.story_service import StoryService
        from backend.api import arq_pool as arq_pool_module

        # Create real ARQ pool
        pool = await create_pool(RedisSettings())
        arq_pool_module.set_pool(pool)

        try:
            # Create mock repository
            mock_repo = MagicMock()
            mock_repo.create_story = AsyncMock()

            service = StoryService(mock_repo)

            with patch("backend.config.get_inference_model_name", return_value="test-model"):
                story_id = await service.create_story_job("Test integration goal")

            # Verify story was created in DB
            mock_repo.create_story.assert_called_once()
            call_kwargs = mock_repo.create_story.call_args.kwargs
            assert call_kwargs["goal"] == "Test integration goal"
            assert call_kwargs["story_id"] == story_id

            # Verify job exists in Redis
            # Give it a moment to enqueue
            await asyncio.sleep(0.1)

            # Check that job keys exist in Redis (ARQ creates job:* keys)
            keys = await pool.keys("arq:job:*")
            assert len(keys) > 0, "Job should be in Redis"

        finally:
            # Clean up
            await pool.flushdb()
            await pool.aclose()
            arq_pool_module._pool = None


class TestEndToEndFlow:
    """End-to-end tests for the complete story generation flow."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_flow_with_mocked_generation(self, skip_without_redis):
        """Test complete flow: API enqueue -> worker process -> DB update."""
        from backend.api.services.story_service import StoryService
        from backend.api.services.story_generation import generate_story
        from backend.api import arq_pool as arq_pool_module
        from backend.worker import generate_story_task

        # Create real ARQ pool
        pool = await create_pool(RedisSettings())
        arq_pool_module.set_pool(pool)

        try:
            # Mock repository
            mock_repo = MagicMock()
            mock_repo.create_story = AsyncMock()

            # Create service and enqueue job
            service = StoryService(mock_repo)

            with patch("backend.config.get_inference_model_name", return_value="test-model"):
                story_id = await service.create_story_job("End to end test story")

            # Now simulate worker processing with mocked generation
            with patch("backend.worker.generate_story", new_callable=AsyncMock) as mock_gen:
                ctx = {"job_id": "e2e-test"}
                result = await generate_story_task(
                    ctx,
                    story_id=story_id,
                    goal="End to end test story",
                )

                assert result["status"] == "completed"
                assert result["story_id"] == story_id
                mock_gen.assert_called_once_with(
                    story_id=story_id,
                    goal="End to end test story",
                    target_age_range="4-7",
                    generation_type="illustrated",
                    quality_threshold=7,
                    max_attempts=3,
                )

        finally:
            await pool.flushdb()
            await pool.aclose()
            arq_pool_module._pool = None
