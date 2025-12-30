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
