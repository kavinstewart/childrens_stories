"""
Standalone spread regeneration logic.

This module contains the core spread regeneration function that can be called
from ARQ worker. Uses a shared database pool passed from the caller.
"""

import json
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import asyncpg

from ..config import STORIES_DIR
from ..logging import story_logger
from ..database.repository import SpreadRegenJobRepository, StoryRepository
from backend.core.cost_tracking import track_costs


async def regenerate_spread(
    job_id: str,
    story_id: str,
    spread_number: int,
    custom_prompt: Optional[str] = None,
    pool: Optional[asyncpg.Pool] = None,
) -> None:
    """
    Regenerate a single spread illustration and update the story.

    Args:
        job_id: ID of the regeneration job
        story_id: ID of the story
        spread_number: Which spread to regenerate (1-12)
        custom_prompt: Optional custom prompt to use instead of the default composed prompt.
                      If provided, bypasses the template and uses this prompt directly.
        pool: Database connection pool (required)

    Raises:
        ValueError: If pool is not provided
    """
    if pool is None:
        raise ValueError("Database pool is required")

    # Import here to avoid circular imports and slow startup
    from backend.core.modules.spread_illustrator import SpreadIllustrator
    from backend.core.modules.illustration_styles import DEFAULT_FALLBACK_STYLE
    from backend.core.types import StorySpread, StoryMetadata, StoryReferenceSheets, StyleDefinition

    start_time = time.time()

    try:
        # Log start
        story_logger.generation_started(f"{story_id}/spread_{spread_number}", "spread_regeneration")

        # Update job status to running
        async with pool.acquire() as conn:
            regen_repo = SpreadRegenJobRepository(conn)
            await regen_repo.update_status(
                job_id,
                "running",
                started_at=datetime.now(timezone.utc),
            )

        # Fetch story data
        async with pool.acquire() as conn:
            repo = StoryRepository(conn)
            regen_repo = SpreadRegenJobRepository(conn)
            story = await repo.get_story(story_id)
            if not story:
                raise ValueError(f"Story {story_id} not found")

            spread_data = await regen_repo.get_spread(story_id, spread_number)
            if not spread_data:
                raise ValueError(f"Spread {spread_number} not found in story {story_id}")

        # Build spread object for illustrator using centralized DB->domain mapping
        spread = StorySpread.from_db_record(spread_data)

        # Build metadata from story data
        # Use stored illustration style if available, otherwise fall back to default
        illustration_style = None
        if story.metadata and story.metadata.illustration_style:
            # Use the original style from the story
            stored_style = story.metadata.illustration_style
            illustration_style = StyleDefinition(
                name=stored_style.name,
                description=stored_style.description,
                prompt_prefix=stored_style.prompt_prefix,
                best_for=stored_style.best_for,
                lighting_direction=stored_style.lighting_direction,
            )
        else:
            # Fall back to default style for older stories without stored style
            illustration_style = DEFAULT_FALLBACK_STYLE

        # Build entity_bibles from character_references for spread illustration
        # This is needed for _get_characters_for_spread() to work correctly
        entity_bibles = {}
        if story.character_references:
            from backend.core.types import EntityBible
            for char_ref in story.character_references:
                if char_ref.bible:
                    # char_ref.bible is a dict from JSON storage
                    entity_bibles[char_ref.character_name] = EntityBible.from_dict(char_ref.bible)

        metadata = None
        if story.metadata:
            metadata = StoryMetadata(
                title=story.metadata.title,
                illustration_style=illustration_style,
                entity_bibles=entity_bibles,
            )

        # Load character reference sheets if available
        reference_sheets = await _load_character_refs(story_id, story)

        # Track costs during illustration (handles start/clear lifecycle)
        with track_costs() as costs:
            # Create illustrator and generate new image
            illustrator = SpreadIllustrator()
            image_bytes = illustrator.illustrate_spread(
                spread=spread,
                outline=metadata,
                reference_sheets=reference_sheets,
                debug=True,
                custom_prompt=custom_prompt,
            )

        # Before saving, verify story still exists (prevents orphaned files if deleted mid-regen)
        async with pool.acquire() as conn:
            repo = StoryRepository(conn)
            if not await repo.get_story(story_id):
                raise ValueError(f"Story {story_id} was deleted during regeneration")

        # Save new image atomically (write to temp, then rename)
        await _save_image_atomically(story_id, spread_number, image_bytes, pool)

        # Update job status to completed with cost data (captured after context exit)
        async with pool.acquire() as conn:
            regen_repo = SpreadRegenJobRepository(conn)
            await regen_repo.update_status(
                job_id,
                "completed",
                completed_at=datetime.now(timezone.utc),
                usage_json=json.dumps(costs.usage_dict) if costs.usage_dict else None,
                cost_usd=costs.cost_usd,
            )

        # Log completion
        duration = time.time() - start_time
        story_logger.generation_completed(f"{story_id}/spread_{spread_number}", duration)

    except Exception as e:
        # Log failure
        story_logger.generation_failed(f"{story_id}/spread_{spread_number}", e, "regeneration")

        # Update job status to failed
        async with pool.acquire() as conn:
            regen_repo = SpreadRegenJobRepository(conn)
            await regen_repo.update_status(
                job_id,
                "failed",
                completed_at=datetime.now(timezone.utc),
                error_message=str(e),
            )
        raise


async def _load_character_refs(story_id: str, story) -> Optional["StoryReferenceSheets"]:
    """Load character reference sheets from filesystem."""
    from backend.core.types import CharacterReferenceSheet, StoryReferenceSheets

    refs_dir = STORIES_DIR / story_id / "character_refs"
    if not refs_dir.exists() or not story.character_references:
        return None

    character_sheets = {}
    for char_ref in story.character_references:
        # Find the reference image file
        # Entity IDs in DB use @ prefix (@e1) but files use _ prefix (_e1_reference.png)
        # Normalize by replacing @ with _ for file matching
        char_name = char_ref.character_name
        file_search_name = char_name.replace("@", "_").lower()

        for path in refs_dir.glob("*_reference.png"):
            if file_search_name in path.stem.lower():
                image_bytes = path.read_bytes()
                character_sheets[char_name] = CharacterReferenceSheet(
                    character_name=char_name,
                    reference_image=image_bytes,
                    prompt_used="",  # Not stored in DB currently
                    character_description=char_ref.character_description or "",
                )
                break

    if not character_sheets:
        return None

    # Get story title from metadata or use a fallback
    story_title = story.metadata.title if story.metadata else story.title or "Untitled"

    return StoryReferenceSheets(
        story_title=story_title,
        character_sheets=character_sheets,
    )


async def _save_image_atomically(
    story_id: str,
    spread_number: int,
    image_bytes: bytes,
    pool: asyncpg.Pool,
) -> None:
    """Save regenerated spread image atomically to filesystem and database.

    Uses temp file + rename pattern to prevent broken images on failure.
    """
    story_dir = STORIES_DIR / story_id
    images_dir = story_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    final_path = images_dir / f"spread_{spread_number:02d}.png"

    # Write to temp file first, then atomically rename
    with tempfile.NamedTemporaryFile(
        dir=images_dir,
        suffix=".png",
        delete=False,
    ) as tmp:
        tmp.write(image_bytes)
        tmp.flush()
        temp_path = Path(tmp.name)

    # Atomic rename (same filesystem, so this is atomic on POSIX)
    shutil.move(str(temp_path), str(final_path))

    # Update database with new path and timestamp
    async with pool.acquire() as conn:
        regen_repo = SpreadRegenJobRepository(conn)
        await regen_repo.save_regenerated_spread(
            story_id=story_id,
            spread_number=spread_number,
            illustration_path=str(final_path),
        )
