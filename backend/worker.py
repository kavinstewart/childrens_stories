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
from backend.api.database.repository import SpreadRegenJobRepository

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
    Cron task to clean up stale spread regeneration jobs.

    Runs every minute to mark jobs as failed if they've been:
    - pending for > 2 minutes
    - running for > 12 minutes
    """
    dsn = _get_database_dsn()
    if not dsn:
        logger.warning("DATABASE_URL not set, skipping stale job cleanup")
        return {"cleaned": 0}

    try:
        conn = await asyncpg.connect(dsn)
        try:
            regen_repo = SpreadRegenJobRepository(conn)
            count = await regen_repo.cleanup_stale_jobs()
            if count > 0:
                logger.info(f"Cleaned up {count} stale spread regeneration job(s)")
            return {"cleaned": count}
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Failed to cleanup stale jobs: {e}")
        return {"cleaned": 0, "error": str(e)}


async def startup(ctx: dict[str, Any]) -> None:
    """Called when worker starts up."""
    logger.info("ARQ worker starting up")

    # Cleanup any jobs left in bad state from previous crash
    dsn = _get_database_dsn()
    if not dsn:
        logger.warning("DATABASE_URL not set, skipping startup cleanup")
        return

    try:
        conn = await asyncpg.connect(dsn)
        try:
            regen_repo = SpreadRegenJobRepository(conn)
            count = await regen_repo.cleanup_stale_jobs()
            if count > 0:
                logger.info(f"Startup cleanup: marked {count} stale job(s) as failed")
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Failed startup cleanup: {e}")


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
