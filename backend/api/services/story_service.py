"""Story service for generation and persistence."""

import uuid

from ..database.repository import StoryRepository
from ..arq_pool import get_pool as get_arq_pool


class StoryService:
    """Service for creating and managing story generation jobs."""

    def __init__(self, repo: StoryRepository):
        self.repo = repo

    # Hardcoded generation defaults (not exposed via API)
    DEFAULT_TARGET_AGE_RANGE = "4-7"
    DEFAULT_GENERATION_TYPE = "illustrated"
    DEFAULT_QUALITY_THRESHOLD = 7
    DEFAULT_MAX_ATTEMPTS = 3

    async def create_story_job(self, goal: str) -> str:
        """
        Create a new story generation job.

        Creates a pending record in the database and enqueues an ARQ job
        to generate the story in the background.

        Args:
            goal: The learning goal or theme for the story

        Returns:
            The story ID which can be used to poll for status.
        """
        # Import here to avoid circular imports
        from backend.config import get_inference_model_name

        story_id = str(uuid.uuid4())
        llm_model = get_inference_model_name()

        # Create pending record in database
        await self.repo.create_story(
            story_id=story_id,
            goal=goal,
            target_age_range=self.DEFAULT_TARGET_AGE_RANGE,
            generation_type=self.DEFAULT_GENERATION_TYPE,
            llm_model=llm_model,
        )

        # Enqueue ARQ job for background generation
        arq_pool = await get_arq_pool()
        await arq_pool.enqueue_job(
            "generate_story_task",
            story_id=story_id,
            goal=goal,
            target_age_range=self.DEFAULT_TARGET_AGE_RANGE,
            generation_type=self.DEFAULT_GENERATION_TYPE,
            quality_threshold=self.DEFAULT_QUALITY_THRESHOLD,
            max_attempts=self.DEFAULT_MAX_ATTEMPTS,
        )

        return story_id

    async def regenerate_spread_job(
        self,
        story_id: str,
        spread_number: int,
    ) -> str:
        """
        Create a new spread regeneration job.

        Creates a pending job record in the database and enqueues an ARQ job
        to regenerate the spread illustration in the background.

        Args:
            story_id: ID of the story containing the spread
            spread_number: Which spread to regenerate (1-12)

        Returns:
            The job ID which can be used to track status.
        """
        # Generate short job ID (8 chars)
        job_id = str(uuid.uuid4())[:8]

        # Create pending job record in database
        await self.repo.create_spread_regen_job(
            job_id=job_id,
            story_id=story_id,
            spread_number=spread_number,
        )

        # Enqueue ARQ job for background regeneration
        arq_pool = await get_arq_pool()
        await arq_pool.enqueue_job(
            "regenerate_spread_task",
            job_id=job_id,
            story_id=story_id,
            spread_number=spread_number,
        )

        return job_id
