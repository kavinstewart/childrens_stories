"""
ARQ worker for background story generation.

Run with: arq backend.worker.WorkerSettings
"""

import logging
import os
from typing import Any

import asyncpg
from arq import cron
from arq.connections import RedisSettings
from dotenv import load_dotenv

# Load environment variables before importing app modules
load_dotenv()

from backend.api.services.story_generation import generate_story
from backend.api.services.spread_regeneration import regenerate_spread
from backend.api.database.repository import SpreadRegenJobRepository, StoryRepository

logger = logging.getLogger(__name__)


def _get_database_dsn() -> str:
    """Get PostgreSQL DSN from environment."""
    dsn = os.getenv("DATABASE_URL", "")
    # Convert SQLAlchemy-style URL to asyncpg format
    return dsn.replace("+asyncpg", "")


async def generate_story_task(
    ctx: dict[str, Any],
    story_id: str,
    goal: str,
    target_age_range: str = "4-7",
    generation_type: str = "illustrated",
) -> dict[str, Any]:
    """
    ARQ task for generating a story.

    This is a thin wrapper around the standalone generate_story function.
    The actual generation logic is in story_generation.py for portability.

    Args:
        ctx: ARQ context (contains job_id, redis connection, etc.)
        story_id: UUID of the story record
        goal: The learning goal or theme for the story
        target_age_range: Target reader age range
        generation_type: "simple", "standard", or "illustrated"

    Returns:
        Dict with story_id and status
    """
    job_id = ctx.get("job_id", "unknown")
    logger.info(f"Starting story generation job {job_id} for story {story_id}")

    try:
        await generate_story(
            story_id=story_id,
            goal=goal,
            target_age_range=target_age_range,
            generation_type=generation_type,
        )
        logger.info(f"Completed story generation job {job_id} for story {story_id}")
        return {"story_id": story_id, "status": "completed"}

    except Exception as e:
        logger.error(f"Failed story generation job {job_id} for story {story_id}: {e}")
        # Re-raise so ARQ marks the job as failed
        raise


async def regenerate_spread_task(
    ctx: dict[str, Any],
    job_id: str,
    story_id: str,
    spread_number: int,
    custom_prompt: str | None = None,
) -> dict[str, Any]:
    """
    ARQ task for regenerating a spread illustration.

    This is a thin wrapper around the standalone regenerate_spread function.

    Args:
        ctx: ARQ context (contains job_id, redis connection, etc.)
        job_id: ID of the regeneration job record
        story_id: UUID of the story
        spread_number: Which spread to regenerate (1-12)
        custom_prompt: Optional custom prompt to use instead of the default

    Returns:
        Dict with job_id and status
    """
    arq_job_id = ctx.get("job_id", "unknown")
    logger.info(f"Starting spread regeneration job {arq_job_id} for story {story_id} spread {spread_number}")

    try:
        await regenerate_spread(
            job_id=job_id,
            story_id=story_id,
            spread_number=spread_number,
            custom_prompt=custom_prompt,
        )
        logger.info(f"Completed spread regeneration job {arq_job_id}")
        return {"job_id": job_id, "status": "completed"}

    except Exception as e:
        logger.error(f"Failed spread regeneration job {arq_job_id}: {e}")
        raise


async def cleanup_stale_jobs_task(ctx: dict[str, Any]) -> dict[str, Any]:
    """
    Cron task to clean up stale jobs in Postgres.

    Runs every minute to mark jobs as failed if they've been:
    - pending for > 2 minutes
    - running for > 12 minutes

    Cleans up both stories and spread regeneration jobs.
    """
    dsn = _get_database_dsn()
    if not dsn:
        logger.warning("DATABASE_URL not set, skipping stale job cleanup")
        return {"cleaned_stories": 0, "cleaned_spreads": 0}

    try:
        conn = await asyncpg.connect(dsn)
        try:
            # Clean up stale stories
            story_repo = StoryRepository(conn)
            story_count = await story_repo.cleanup_stale_stories()
            if story_count > 0:
                logger.info(f"Cleaned up {story_count} stale story job(s)")

            # Clean up stale spread regeneration jobs
            regen_repo = SpreadRegenJobRepository(conn)
            spread_count = await regen_repo.cleanup_stale_jobs()
            if spread_count > 0:
                logger.info(f"Cleaned up {spread_count} stale spread regeneration job(s)")

            return {"cleaned_stories": story_count, "cleaned_spreads": spread_count}
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Failed to cleanup stale jobs: {e}")
        return {"cleaned_stories": 0, "cleaned_spreads": 0, "error": str(e)}


async def startup(ctx: dict[str, Any]) -> None:
    """Called when worker starts up."""
    logger.info("ARQ worker starting up")

    # Cleanup stale Redis keys from previous crash
    # This prevents ghost jobs from blocking the worker
    await _cleanup_stale_redis_keys(ctx)

    # Cleanup any jobs left in bad state from previous crash
    dsn = _get_database_dsn()
    if not dsn:
        logger.warning("DATABASE_URL not set, skipping startup cleanup")
        return

    try:
        conn = await asyncpg.connect(dsn)
        try:
            # Clean up stale stories
            story_repo = StoryRepository(conn)
            story_count = await story_repo.cleanup_stale_stories()
            if story_count > 0:
                logger.info(f"Startup cleanup: marked {story_count} stale story job(s) as failed")

            # Clean up stale spread regeneration jobs
            regen_repo = SpreadRegenJobRepository(conn)
            spread_count = await regen_repo.cleanup_stale_jobs()
            if spread_count > 0:
                logger.info(f"Startup cleanup: marked {spread_count} stale spread job(s) as failed")
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Failed startup cleanup: {e}")


async def _cleanup_stale_redis_keys(ctx: dict[str, Any]) -> None:
    """Clean up stale in-progress keys from crashed workers.

    On worker startup, clears arq:in-progress:* keys (except cron jobs) to allow
    jobs that were running when the previous worker crashed to be picked up again.

    NOTE: All ARQ keys (job, retry, result, in-progress) are STRING type - this is
    correct. Do NOT delete keys based on type checks.
    """
    redis = ctx.get("redis")
    if not redis:
        logger.warning("Redis connection not available in context, skipping Redis cleanup")
        return

    try:
        cleaned = 0

        # Clean up stale in-progress keys (ghost jobs from crashed workers)
        # These keys have TTL and indicate a job is "in progress" - if the worker
        # crashed, these keys prevent the job from being picked up by a new worker
        in_progress_keys = await redis.keys("arq:in-progress:*")
        for key in in_progress_keys:
            # Skip cron job keys (they use keep_cronjob_progress to prevent duplicates)
            if b"cron:" in key:
                continue
            await redis.delete(key)
            cleaned += 1
            logger.debug(f"Deleted stale in-progress key: {key}")

        if cleaned > 0:
            logger.info(f"Startup Redis cleanup: removed {cleaned} stale in-progress key(s)")

    except Exception as e:
        logger.error(f"Failed Redis cleanup: {e}")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Called when worker shuts down."""
    logger.info("ARQ worker shutting down")


class WorkerSettings:
    """ARQ worker configuration."""

    # Task functions to register
    functions = [generate_story_task, regenerate_spread_task]

    # Cron jobs for periodic maintenance
    cron_jobs = [
        # Run stale job cleanup every minute
        cron(cleanup_stale_jobs_task, minute=set(range(60))),
    ]

    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown

    # Redis connection settings
    redis_settings = RedisSettings()

    # Job settings
    max_jobs = 2  # Max concurrent jobs (story generation is resource-intensive)
    job_timeout = 600  # 10 minutes max per job
    max_tries = 3  # Retry transient failures (safety net for @image_retry)

    # Fixed 30-second delay between retries
    # This is a safety net - primary retry with exponential backoff
    # happens at @image_retry decorator level. ARQ retries are for
    # edge cases where errors occur outside the image generation call.
    retry_delay = 30

    # Health check
    health_check_interval = 30
