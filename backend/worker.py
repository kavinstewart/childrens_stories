"""
ARQ worker for background story generation.

Run with: arq backend.worker.WorkerSettings
"""

import logging
from typing import Any

from arq import cron
from arq.connections import RedisSettings
from dotenv import load_dotenv

# Load environment variables before importing app modules
load_dotenv()

from backend.api.services.story_generation import generate_story
from backend.api.services.spread_regeneration import regenerate_spread

logger = logging.getLogger(__name__)


async def generate_story_task(
    ctx: dict[str, Any],
    story_id: str,
    goal: str,
    target_age_range: str = "4-7",
    generation_type: str = "illustrated",
    quality_threshold: int = 7,
    max_attempts: int = 3,
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
        quality_threshold: Minimum score (0-10) to accept
        max_attempts: Maximum generation attempts

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
            quality_threshold=quality_threshold,
            max_attempts=max_attempts,
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
) -> dict[str, Any]:
    """
    ARQ task for regenerating a spread illustration.

    This is a thin wrapper around the standalone regenerate_spread function.

    Args:
        ctx: ARQ context (contains job_id, redis connection, etc.)
        job_id: ID of the regeneration job record
        story_id: UUID of the story
        spread_number: Which spread to regenerate (1-12)

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
        )
        logger.info(f"Completed spread regeneration job {arq_job_id}")
        return {"job_id": job_id, "status": "completed"}

    except Exception as e:
        logger.error(f"Failed spread regeneration job {arq_job_id}: {e}")
        raise


async def startup(ctx: dict[str, Any]) -> None:
    """Called when worker starts up."""
    logger.info("ARQ worker starting up")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Called when worker shuts down."""
    logger.info("ARQ worker shutting down")


class WorkerSettings:
    """ARQ worker configuration."""

    # Task functions to register
    functions = [generate_story_task, regenerate_spread_task]

    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown

    # Redis connection settings
    redis_settings = RedisSettings()

    # Job settings
    max_jobs = 2  # Max concurrent jobs (story generation is resource-intensive)
    job_timeout = 600  # 10 minutes max per job
    max_tries = 1  # Don't retry failed jobs (story is marked failed in DB)

    # Health check
    health_check_interval = 30
