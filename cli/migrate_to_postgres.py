#!/usr/bin/env python3
"""
One-time migration script: SQLite -> PostgreSQL

Migrates all data from the SQLite database to PostgreSQL.
Run this once after setting up the PostgreSQL database.

Usage:
    DATABASE_URL=postgresql+asyncpg://user:pass@host/db poetry run python cli/migrate_to_postgres.py
"""

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from backend.api.config import SQLITE_DB_PATH, DATABASE_URL
from backend.api.database.db import engine, async_session_factory, Base
from backend.api.database.models import (
    Story,
    StorySpread,
    CharacterReference,
    VLMEvaluation,
)


def get_sqlite_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database."""
    if not SQLITE_DB_PATH.exists():
        print(f"SQLite database not found at {SQLITE_DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


async def migrate_stories(sqlite_conn: sqlite3.Connection) -> int:
    """Migrate stories table."""
    cursor = sqlite_conn.execute("SELECT * FROM stories")
    rows = cursor.fetchall()

    async with async_session_factory() as session:
        for row in rows:
            story = Story(
                id=row["id"],
                status=row["status"],
                goal=row["goal"],
                target_age_range=row["target_age_range"],
                generation_type=row["generation_type"],
                llm_model=row["llm_model"],
                title=row["title"],
                word_count=row["word_count"],
                spread_count=row["spread_count"],
                attempts=row["attempts"],
                is_illustrated=bool(row["is_illustrated"]),
                outline_json=row["outline_json"],
                judgment_json=row["judgment_json"],
                progress_json=row["progress_json"] if "progress_json" in row.keys() else None,
                error_message=row["error_message"],
                # Handle datetime conversions
                created_at=row["created_at"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
            )
            session.add(story)

        await session.commit()

    return len(rows)


async def migrate_spreads(sqlite_conn: sqlite3.Connection) -> int:
    """Migrate story_spreads table."""
    cursor = sqlite_conn.execute("SELECT * FROM story_spreads")
    rows = cursor.fetchall()

    async with async_session_factory() as session:
        for row in rows:
            spread = StorySpread(
                id=row["id"],
                story_id=row["story_id"],
                spread_number=row["spread_number"],
                text=row["text"],
                word_count=row["word_count"],
                was_revised=bool(row["was_revised"]),
                page_turn_note=row["page_turn_note"],
                illustration_prompt=row["illustration_prompt"],
                illustration_path=row["illustration_path"],
            )
            session.add(spread)

        await session.commit()

    return len(rows)


async def migrate_character_refs(sqlite_conn: sqlite3.Connection) -> int:
    """Migrate character_references table."""
    cursor = sqlite_conn.execute("SELECT * FROM character_references")
    rows = cursor.fetchall()

    async with async_session_factory() as session:
        for row in rows:
            ref = CharacterReference(
                id=row["id"],
                story_id=row["story_id"],
                character_name=row["character_name"],
                character_description=row["character_description"],
                reference_image_path=row["reference_image_path"],
            )
            session.add(ref)

        await session.commit()

    return len(rows)


async def migrate_vlm_evals(sqlite_conn: sqlite3.Connection) -> int:
    """Migrate vlm_evaluations table."""
    try:
        cursor = sqlite_conn.execute("SELECT * FROM vlm_evaluations")
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        # Table might not exist in older DBs
        print("  vlm_evaluations table not found, skipping...")
        return 0

    async with async_session_factory() as session:
        for row in rows:
            evaluation = VLMEvaluation(
                id=row["id"],
                story_id=row["story_id"],
                spread_number=row["spread_number"],
                prompt=row["prompt"],
                image_path=row["image_path"],
                character_ref_paths=row["character_ref_paths"],
                check_text_free=bool(row["check_text_free"]),
                check_characters=bool(row["check_characters"]),
                check_composition=bool(row["check_composition"]),
                vlm_model=row["vlm_model"],
                vlm_raw_response=row["vlm_raw_response"],
                vlm_overall_pass=bool(row["vlm_overall_pass"]) if row["vlm_overall_pass"] is not None else None,
                vlm_text_free=bool(row["vlm_text_free"]) if row["vlm_text_free"] is not None else None,
                vlm_character_match_score=row["vlm_character_match_score"],
                vlm_scene_accuracy_score=row["vlm_scene_accuracy_score"],
                vlm_composition_score=row["vlm_composition_score"],
                vlm_style_score=row["vlm_style_score"],
                vlm_issues=row["vlm_issues"],
                human_verdict=bool(row["human_verdict"]) if row["human_verdict"] is not None else None,
                human_notes=row["human_notes"],
                annotated_at=row["annotated_at"],
                created_at=row["created_at"],
            )
            session.add(evaluation)

        await session.commit()

    return len(rows)


async def main():
    """Run the migration."""
    print("=" * 60)
    print("SQLite to PostgreSQL Migration")
    print("=" * 60)

    # Validate configuration
    if not DATABASE_URL:
        print("\nError: DATABASE_URL environment variable not set!")
        print("Set it to your PostgreSQL connection string:")
        print("  export DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname")
        sys.exit(1)

    print(f"\nSource: {SQLITE_DB_PATH}")
    print(f"Target: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")

    # Confirm before proceeding
    response = input("\nProceed with migration? [y/N] ")
    if response.lower() != "y":
        print("Migration cancelled.")
        sys.exit(0)

    # Create tables in PostgreSQL
    print("\n1. Creating tables in PostgreSQL...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("   Done.")

    # Connect to SQLite
    sqlite_conn = get_sqlite_connection()

    # Migrate each table
    print("\n2. Migrating data...")

    print("   - stories...", end=" ", flush=True)
    count = await migrate_stories(sqlite_conn)
    print(f"{count} rows")

    print("   - story_spreads...", end=" ", flush=True)
    count = await migrate_spreads(sqlite_conn)
    print(f"{count} rows")

    print("   - character_references...", end=" ", flush=True)
    count = await migrate_character_refs(sqlite_conn)
    print(f"{count} rows")

    print("   - vlm_evaluations...", end=" ", flush=True)
    count = await migrate_vlm_evals(sqlite_conn)
    print(f"{count} rows")

    # Close connections
    sqlite_conn.close()
    await engine.dispose()

    print("\n" + "=" * 60)
    print("Migration complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Verify data in PostgreSQL")
    print("2. Update your .env file with DATABASE_URL")
    print("3. Restart the API server")
    print("4. (Optional) Back up and remove the SQLite database")


if __name__ == "__main__":
    asyncio.run(main())
