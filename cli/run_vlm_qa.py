#!/usr/bin/env python3
"""
Run VLM Judge QA process on an existing story.

Usage:
    poetry run python cli/run_vlm_qa.py <story_id_or_title>
    poetry run python cli/run_vlm_qa.py "The General's Glasses"
    poetry run python cli/run_vlm_qa.py 463b8961-c6d5-4f92-940a-f16a2bf473ae
"""

import sys
import sqlite3
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from PIL import Image

from backend.core.modules.image_qa import ImageQA, QAVerdict
from backend.core.types import StoryReferenceSheets, CharacterReferenceSheet


def get_story_by_id_or_title(db_path: Path, identifier: str) -> dict | None:
    """Find story by UUID or title (case-insensitive partial match)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Try exact ID match first
    cursor.execute("SELECT * FROM stories WHERE id = ?", (identifier,))
    row = cursor.fetchone()
    if row:
        conn.close()
        return dict(row)

    # Try title match (case-insensitive, partial)
    cursor.execute(
        "SELECT * FROM stories WHERE LOWER(title) LIKE ?",
        (f"%{identifier.lower()}%",),
    )
    row = cursor.fetchone()
    if row:
        conn.close()
        return dict(row)

    conn.close()
    return None


def get_story_spreads(db_path: Path, story_id: str) -> list[dict]:
    """Get all spreads for a story."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT spread_number, text, illustration_prompt, illustration_path
        FROM story_spreads
        WHERE story_id = ?
        ORDER BY spread_number
        """,
        (story_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_character_references(db_path: Path, story_id: str) -> list[dict]:
    """Get character references for a story."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT character_name, character_description, reference_image_path
        FROM character_references
        WHERE story_id = ?
        """,
        (story_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def build_reference_sheets(
    story_title: str, character_refs: list[dict]
) -> StoryReferenceSheets:
    """Build StoryReferenceSheets from database records."""
    sheets = StoryReferenceSheets(story_title=story_title)

    for ref in character_refs:
        ref_path = Path(ref["reference_image_path"])
        if not ref_path.exists():
            print(f"  Warning: Reference image not found: {ref_path}")
            continue

        with open(ref_path, "rb") as f:
            image_bytes = f.read()

        sheets.character_sheets[ref["character_name"]] = CharacterReferenceSheet(
            character_name=ref["character_name"],
            reference_image=image_bytes,
            character_description=ref["character_description"] or "",
        )

    return sheets


def run_vlm_qa(story_identifier: str, enable_logging: bool = True):
    """Run VLM Judge QA on all spreads of a story."""
    db_path = Path("data/stories.db")
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return

    # Find the story
    story = get_story_by_id_or_title(db_path, story_identifier)
    if not story:
        print(f"Error: Story not found: {story_identifier}")
        return

    story_id = story["id"]
    story_title = story["title"] or "Untitled"

    print(f"\n{'='*60}")
    print(f"VLM Judge QA for: {story_title}")
    print(f"Story ID: {story_id}")
    print(f"{'='*60}\n")

    # Get spreads and character references
    spreads = get_story_spreads(db_path, story_id)
    if not spreads:
        print("Error: No spreads found for this story")
        return

    character_refs = get_character_references(db_path, story_id)
    reference_sheets = build_reference_sheets(story_title, character_refs)

    print(f"Found {len(spreads)} spreads")
    print(f"Found {len(reference_sheets.character_sheets)} character references:")
    for name in reference_sheets.character_sheets:
        print(f"  - {name}")
    print()

    # Initialize QA system
    qa = ImageQA(
        require_text_free=True,
        min_character_score=4,
        min_scene_score=3,
        enable_logging=enable_logging,
    )

    # Run QA on each spread
    results = []
    for spread in spreads:
        spread_num = spread["spread_number"]
        prompt = spread["illustration_prompt"]
        image_path = Path(spread["illustration_path"])

        if not image_path.exists():
            print(f"Spread {spread_num:02d}: ❌ Image not found: {image_path}")
            continue

        print(f"Spread {spread_num:02d}: Evaluating...", end=" ", flush=True)

        try:
            image = Image.open(image_path)

            result = qa.evaluate(
                image=image,
                prompt=prompt,
                image_id=f"spread_{spread_num:02d}",
                reference_sheets=reference_sheets if reference_sheets.character_sheets else None,
                story_id=story_id,
                spread_number=spread_num,
            )

            results.append((spread_num, result))

            # Print result
            if result.verdict == QAVerdict.PASS:
                print("✅ PASS")
                dc = result.detailed_check
                if dc:
                    print(f"       Character: {dc.character_match_score}/5, Scene: {dc.scene_accuracy_score}/5, Composition: {dc.composition_score}/5")
            else:
                print(f"❌ {result.verdict.value}")
                for reason in result.failure_reasons:
                    print(f"       - {reason}")

        except Exception as e:
            print(f"❌ Error: {e}")

    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for _, r in results if r.verdict == QAVerdict.PASS)
    total = len(results)

    print(f"Passed: {passed}/{total} spreads")

    if passed < total:
        print("\nFailed spreads:")
        for spread_num, result in results:
            if result.verdict != QAVerdict.PASS:
                print(f"  Spread {spread_num}: {result.verdict.value}")
                for reason in result.failure_reasons:
                    print(f"    - {reason}")

    # Score breakdown
    if results:
        char_scores = [r.detailed_check.character_match_score for _, r in results if r.detailed_check]
        scene_scores = [r.detailed_check.scene_accuracy_score for _, r in results if r.detailed_check]
        comp_scores = [r.detailed_check.composition_score for _, r in results if r.detailed_check]
        style_scores = [r.detailed_check.style_score for _, r in results if r.detailed_check]

        if char_scores:
            print(f"\nAverage Scores:")
            print(f"  Character Consistency: {sum(char_scores)/len(char_scores):.1f}/5")
            print(f"  Scene Accuracy: {sum(scene_scores)/len(scene_scores):.1f}/5")
            print(f"  Composition: {sum(comp_scores)/len(comp_scores):.1f}/5")
            print(f"  Style: {sum(style_scores)/len(style_scores):.1f}/5")

    if enable_logging:
        print(f"\n📝 Evaluations logged to database for human annotation")
        print(f"   Run the API and check /admin/vlm-evaluations to annotate")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: poetry run python cli/run_vlm_qa.py <story_id_or_title>")
        print("\nAvailable stories:")
        db_path = Path("data/stories.db")
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, title FROM stories WHERE title IS NOT NULL")
            for row in cursor.fetchall():
                print(f"  - {row[1]} ({row[0]})")
            conn.close()
        sys.exit(1)

    story_identifier = sys.argv[1]
    enable_logging = "--no-log" not in sys.argv

    run_vlm_qa(story_identifier, enable_logging=enable_logging)
