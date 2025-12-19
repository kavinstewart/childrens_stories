"""Story service for generation and persistence."""

import uuid
import json
import asyncio
from datetime import datetime
from pathlib import Path
from dataclasses import asdict
from typing import Optional

from ..database.repository import StoryRepository
from ..config import STORIES_DIR
from .job_manager import job_manager


class StoryService:
    """Service for creating and managing story generation jobs."""

    def __init__(self, repo: StoryRepository):
        self.repo = repo

    async def create_story_job(
        self,
        goal: str,
        target_age_range: str,
        generation_type: str,
        quality_threshold: int,
        max_attempts: int,
    ) -> str:
        """
        Create a new story generation job.

        Returns the job/story ID which can be used to poll for status.
        """
        # Import here to avoid circular imports
        from backend.config import get_inference_model_name

        story_id = str(uuid.uuid4())
        llm_model = get_inference_model_name()

        # Create pending record in database
        await self.repo.create_story(
            story_id=story_id,
            goal=goal,
            target_age_range=target_age_range,
            generation_type=generation_type,
            llm_model=llm_model,
        )

        # Submit background job
        job_manager.submit(
            story_id,
            self._run_generation_sync,
            story_id,
            goal,
            target_age_range,
            generation_type,
            quality_threshold,
            max_attempts,
        )

        return story_id

    def _run_generation_sync(
        self,
        story_id: str,
        goal: str,
        target_age_range: str,
        generation_type: str,
        quality_threshold: int,
        max_attempts: int,
    ) -> None:
        """
        Synchronous wrapper for story generation.

        Runs in a background thread, creates its own event loop for async DB calls.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(
                self._generate_story(
                    story_id,
                    goal,
                    target_age_range,
                    generation_type,
                    quality_threshold,
                    max_attempts,
                )
            )
        finally:
            loop.close()

    async def _generate_story(
        self,
        story_id: str,
        goal: str,
        target_age_range: str,
        generation_type: str,
        quality_threshold: int,
        max_attempts: int,
    ) -> None:
        """Actual story generation with DB updates."""
        # Import here to avoid circular imports and slow startup
        # Using absolute imports to survive directory restructure
        import dspy
        from backend.core.programs.story_generator import StoryGenerator
        from backend.config import get_inference_lm

        # Update status to running
        await self.repo.update_status(
            story_id,
            "running",
            started_at=datetime.utcnow(),
        )

        try:
            # Get the LM for this generation
            lm = get_inference_lm()

            # Create generator with explicit LM
            generator = StoryGenerator(
                quality_threshold=quality_threshold,
                max_attempts=max_attempts,
                lm=lm,
            )

            # Generate based on type
            if generation_type == "simple":
                story = generator.generate_simple(goal)
            elif generation_type == "illustrated":
                story = generator.generate_illustrated(
                    goal,
                    target_age_range,
                    skip_quality_loop=False,
                    use_image_qa=True,
                    max_image_attempts=3,
                )
            else:  # standard
                story = generator.forward(
                    goal,
                    target_age_range,
                    skip_quality_loop=False,
                )

            # Save to database and filesystem
            await self._save_story(story_id, story)

        except Exception as e:
            # Update status to failed with error message
            await self.repo.update_status(
                story_id,
                "failed",
                completed_at=datetime.utcnow(),
                error_message=str(e),
            )
            raise

    async def _save_story(self, story_id: str, story) -> None:
        """Save generated story to database and filesystem."""
        # Create story directory for images if illustrated
        story_dir = STORIES_DIR / story_id
        story_dir.mkdir(parents=True, exist_ok=True)

        # Prepare spreads data
        spreads_data = []
        for spread in story.spreads:
            spread_data = {
                "spread_number": spread.spread_number,
                "text": spread.text,
                "word_count": spread.word_count,
                "was_revised": spread.was_revised,
                "page_turn_note": getattr(spread, 'page_turn_note', ''),
                "illustration_prompt": spread.illustration_prompt,
                "illustration_path": None,
            }

            # Save illustration if present
            if spread.illustration_image:
                images_dir = story_dir / "images"
                images_dir.mkdir(exist_ok=True)
                img_path = images_dir / f"spread_{spread.spread_number:02d}.png"
                img_path.write_bytes(spread.illustration_image)
                spread_data["illustration_path"] = str(img_path)

            spreads_data.append(spread_data)

        # Prepare character refs data
        char_refs_data = None
        if story.reference_sheets:
            char_refs_data = []
            refs_dir = story_dir / "character_refs"
            refs_dir.mkdir(exist_ok=True)

            for name, sheet in story.reference_sheets.character_sheets.items():
                ref_path = refs_dir / f"{_safe_filename(name)}_reference.png"
                ref_path.write_bytes(sheet.reference_image)

                char_refs_data.append({
                    "character_name": name,
                    "character_description": sheet.character_description,
                    "reference_image_path": str(ref_path),
                })

        # Serialize outline
        outline_dict = {
            "title": story.outline.title,
            "protagonist_goal": story.outline.protagonist_goal,
            "stakes": story.outline.stakes,
            "characters": story.outline.characters,
            "setting": story.outline.setting,
            "emotional_arc": story.outline.emotional_arc,
            "plot_summary": story.outline.plot_summary,
            "moral": story.outline.moral,
            "spread_count": story.outline.spread_count,
        }

        # Serialize judgment if present
        judgment_dict = None
        if story.judgment:
            judgment_dict = {
                "overall_score": story.judgment.overall_score,
                "verdict": story.judgment.verdict,
                "engagement_score": story.judgment.engagement_score,
                "read_aloud_score": story.judgment.read_aloud_score,
                "emotional_truth_score": story.judgment.emotional_truth_score,
                "coherence_score": story.judgment.coherence_score,
                "chekhov_score": story.judgment.chekhov_score,
                "has_critical_failures": story.judgment.has_critical_failures,
                "specific_problems": story.judgment.specific_problems,
            }

        # Save to database
        await self.repo.save_completed_story(
            story_id=story_id,
            title=story.title,
            word_count=story.word_count,
            spread_count=story.spread_count,
            attempts=story.attempts,
            is_illustrated=story.is_illustrated,
            outline_json=json.dumps(outline_dict),
            judgment_json=json.dumps(judgment_dict) if judgment_dict else None,
            spreads=spreads_data,
            character_refs=char_refs_data,
        )


def _safe_filename(name: str) -> str:
    """Convert a string to a safe filename."""
    return "".join(c if c.isalnum() else "_" for c in name)
