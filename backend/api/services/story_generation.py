"""
Standalone story generation logic.

This module contains the core story generation function that can be called
from any task runner (ARQ, Celery, or direct invocation). It handles its
own database connections to avoid event loop conflicts.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import asyncpg

from ..config import DATABASE_URL, STORIES_DIR, story_logger
from ..database.repository import StoryRepository
from .progress_tracker import ProgressTracker


async def generate_story(
    story_id: str,
    goal: str,
    target_age_range: str = "4-7",
    generation_type: str = "illustrated",
    quality_threshold: int = 7,
    max_attempts: int = 3,
    on_progress: Optional[Callable[[str, str, int, int], None]] = None,
) -> None:
    """
    Generate a story and save it to the database.

    This is the main entry point for story generation. It creates its own
    database connections to avoid event loop conflicts when called from
    background workers.

    Args:
        story_id: UUID of the story record (must already exist in DB)
        goal: The learning goal or theme for the story
        target_age_range: Target reader age range (default "4-7")
        generation_type: "simple", "standard", or "illustrated"
        quality_threshold: Minimum score (0-10) to accept a story
        max_attempts: Maximum generation attempts
        on_progress: Optional callback for progress updates
    """
    # Import here to avoid circular imports and slow startup
    from backend.core.programs.story_generator import StoryGenerator
    from backend.config import get_inference_lm

    start_time = time.time()

    # Create a dedicated connection pool for this task
    # This avoids event loop conflicts with the main FastAPI thread
    # Convert SQLAlchemy-style URL to asyncpg format
    dsn = DATABASE_URL.replace("+asyncpg", "")
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)

    # Create progress tracker
    tracker = ProgressTracker(story_id)

    try:
        # Log generation start
        story_logger.generation_started(story_id, generation_type)

        # Update status to running
        async with pool.acquire() as conn:
            repo = StoryRepository(conn)
            await repo.update_status(
                story_id,
                "running",
                started_at=datetime.now(timezone.utc),
            )

        # Initial progress update
        await tracker.update_async("outline", "Crafting your story outline...")

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
            await tracker.update_async("outline", "Crafting your story outline...")
            story = generator.generate_simple(goal)
            await tracker.update_async("spreads", "Story complete", completed=1, total=1)

        elif generation_type == "illustrated":
            # Get reference to running event loop for thread-safe scheduling
            loop = asyncio.get_running_loop()

            # Create progress callback that updates the tracker
            # Uses run_coroutine_threadsafe since the callback is called from
            # within a sync function running in a thread pool
            def progress_callback(stage: str, detail: str, completed: int, total: int):
                asyncio.run_coroutine_threadsafe(
                    tracker.update_async(stage, detail, completed, total),
                    loop
                )
                # Also call user callback if provided
                if on_progress:
                    on_progress(stage, detail, completed, total)

            # Run the blocking generate_illustrated in a thread pool so the
            # event loop stays responsive and can process progress updates
            story = await asyncio.to_thread(
                generator.generate_illustrated,
                goal,
                target_age_range,
                skip_quality_loop=False,
                use_image_qa=True,
                max_image_attempts=3,
                debug=True,
                on_progress=progress_callback,
            )

        else:  # standard
            await tracker.update_async("outline", "Crafting your story outline...")
            story = generator.forward(
                goal,
                target_age_range,
                skip_quality_loop=False,
            )
            await tracker.update_async("quality", "Story generation complete")

        # Save to database and filesystem
        await _save_story(story_id, story, pool)

        # Log completion
        duration = time.time() - start_time
        story_logger.generation_completed(story_id, duration)

    except Exception as e:
        # Log and track failure
        story_logger.generation_failed(story_id, e)
        await tracker.update_async("failed", f"Generation failed: {type(e).__name__}")

        # Update status to failed with error message
        async with pool.acquire() as conn:
            repo = StoryRepository(conn)
            await repo.update_status(
                story_id,
                "failed",
                completed_at=datetime.now(timezone.utc),
                error_message=str(e),
            )
        raise

    finally:
        # Clean up resources
        await tracker.close()
        await pool.close()


async def _save_story(
    story_id: str,
    story,
    pool: asyncpg.Pool,
) -> None:
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
            "page_turn_note": getattr(spread, "page_turn_note", ""),
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

            char_refs_data.append(
                {
                    "character_name": name,
                    "character_description": sheet.character_description,
                    "reference_image_path": str(ref_path),
                }
            )

    # Serialize outline
    outline_dict = {
        "title": story.outline.title,
        "characters": story.outline.characters,
        "setting": story.outline.setting,
        "plot_summary": story.outline.plot_summary,
        "spread_count": story.outline.spread_count,
    }

    # Include illustration style if available (for regeneration consistency)
    if story.outline.illustration_style:
        style = story.outline.illustration_style
        outline_dict["illustration_style"] = {
            "name": style.name,
            "description": style.description,
            "prompt_prefix": style.prompt_prefix,
            "best_for": style.best_for,
            "lighting_direction": style.lighting_direction,
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
    async with pool.acquire() as conn:
        repo = StoryRepository(conn)
        await repo.save_completed_story(
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
