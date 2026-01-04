#!/usr/bin/env python3
"""
Regenerate a story with the current pipeline.

This script:
1. Extracts the original goal from the database
2. Deletes the old story record
3. Regenerates using the current StoryGenerator (with all current features)
4. Saves the new story to the database

Usage:
    poetry run python scripts/regenerate_story.py <story_id>
    poetry run python scripts/regenerate_story.py 463b8961-c6d5-4f92-940a-f16a2bf473ae
"""

import argparse
import asyncio
import json
import shutil
import sys
import uuid
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import configure_dspy, get_inference_lm
from backend.api.database.db import get_db
from backend.api.database.repository import StoryRepository
from backend.api.config import STORIES_DIR
from backend.core.programs.story_generator import StoryGenerator


async def get_story_goal(story_id: str) -> tuple[str, str, str]:
    """Get the goal, target_age_range, and generation_type for a story."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT goal, target_age_range, generation_type FROM stories WHERE id = ?",
            (story_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Story {story_id} not found")
        return row["goal"], row["target_age_range"], row["generation_type"]


async def delete_story(story_id: str) -> None:
    """Delete a story from database and filesystem."""
    repo = StoryRepository()

    # Delete from database (CASCADE will handle spreads and character_references)
    deleted = await repo.delete_story(story_id)
    if not deleted:
        raise ValueError(f"Failed to delete story {story_id}")

    # Delete from filesystem
    story_dir = STORIES_DIR / story_id
    if story_dir.exists():
        shutil.rmtree(story_dir)
        print(f"  Deleted story directory: {story_dir}")


async def create_story_record(story_id: str, goal: str, target_age_range: str, generation_type: str, llm_model: str) -> None:
    """Create a new pending story record."""
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO stories (id, goal, target_age_range, generation_type, llm_model, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (story_id, goal, target_age_range, generation_type, llm_model),
        )
        await db.commit()


async def save_story(story_id: str, story, goal: str) -> None:
    """Save a generated story to database and filesystem."""
    repo = StoryRepository()

    # Create story directory
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
            safe_name = "".join(c if c.isalnum() else "_" for c in name)
            ref_path = refs_dir / f"{safe_name}_reference.png"
            ref_path.write_bytes(sheet.reference_image)

            char_refs_data.append({
                "character_name": name,
                "character_description": sheet.character_description,
                "reference_image_path": str(ref_path),
            })

    # Serialize outline
    outline_dict = {
        "title": story.outline.title,
        "characters": story.outline.characters,
        "setting": story.outline.setting,
        "plot_summary": story.outline.plot_summary,
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


async def main(story_id: str):
    print("=" * 60)
    print(f"Regenerating story: {story_id}")
    print("=" * 60)

    # Step 1: Extract goal from old story
    print("\n1. Extracting goal from old story...")
    goal, target_age_range, generation_type = await get_story_goal(story_id)
    print(f"   Goal: {goal}")
    print(f"   Target age: {target_age_range}")
    print(f"   Generation type: {generation_type}")

    # Step 2: Delete old story
    print("\n2. Deleting old story...")
    await delete_story(story_id)
    print(f"   Deleted story {story_id}")

    # Step 3: Configure DSPy and regenerate
    print("\n3. Regenerating story...")
    configure_dspy(use_reflection_lm=False)
    lm = get_inference_lm()

    generator = StoryGenerator(
        quality_threshold=7,
        max_attempts=3,
        lm=lm,
    )

    # Generate illustrated story
    story = generator.generate_illustrated(
        goal=goal,
        target_age_range=target_age_range,
        skip_quality_loop=False,
        use_image_qa=False,  # Disabled: manual regeneration approach preferred
        max_image_attempts=3,
        debug=True,
    )

    print(f"\n   Generated: '{story.title}'")
    print(f"   Spreads: {len(story.spreads)}")
    print(f"   Word count: {story.word_count}")

    # Step 4: Save new story with same ID
    print("\n4. Saving new story to database...")

    # Create new story record first
    from backend.config import get_inference_model_name
    new_story_id = str(uuid.uuid4())
    await create_story_record(
        story_id=new_story_id,
        goal=goal,
        target_age_range=target_age_range,
        generation_type=generation_type,
        llm_model=get_inference_model_name(),
    )

    # Save the story
    await save_story(new_story_id, story, goal)
    print(f"   Saved with ID: {new_story_id}")

    # Step 5: Print verification
    print("\n" + "=" * 60)
    print("VERIFICATION: Checking present_characters on a few spreads")
    print("=" * 60)

    for i, spread in enumerate(story.spreads):
        if i in [0, 5, 11]:  # Spread 1, 6, and 12
            print(f"\nSpread {spread.spread_number}:")
            print(f"  Text: {spread.text[:100]}..." if len(spread.text) > 100 else f"  Text: {spread.text}")
            print(f"  Illustration: {spread.illustration_prompt[:80]}..." if len(spread.illustration_prompt) > 80 else f"  Illustration: {spread.illustration_prompt}")
            print(f"  present_characters: {spread.present_characters}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\nOriginal Goal: {goal}")
    print(f"\nOld story ID (deleted): {story_id}")
    print(f"New story ID (created): {new_story_id}")
    print(f"Title: {story.title}")

    return story


def parse_args():
    parser = argparse.ArgumentParser(
        description="Regenerate a story with the current pipeline"
    )
    parser.add_argument(
        "story_id",
        help="UUID of the story to regenerate",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.story_id))
