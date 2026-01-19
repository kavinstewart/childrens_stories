#!/usr/bin/env python3
"""
Diagnostic script to check character reference resolution for a story.
"""
import asyncio
import asyncpg
import os
import sys
import json
import re
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv('.env')


async def diagnose_story(story_id: str):
    db_url = os.environ['DATABASE_URL'].replace('postgresql+asyncpg://', 'postgresql://')
    pool = await asyncpg.create_pool(db_url)

    # Get story data
    story = await pool.fetchrow(
        'SELECT title, outline_json FROM stories WHERE id = $1',
        story_id
    )

    if not story:
        print(f"Story {story_id} not found")
        await pool.close()
        return

    print(f"Story: {story['title']}")
    print()

    # Parse outline for character bibles
    outline = json.loads(story['outline_json']) if story['outline_json'] else {}
    character_bibles = outline.get('character_bibles', [])

    print("=== Character Bibles ===")
    for bible in character_bibles:
        print(f"  Name: {bible.get('name')}")
        print(f"  Aliases: {bible.get('aliases', [])}")
        print()

    # Get spreads
    spreads = await pool.fetch(
        'SELECT spread_number, illustration_prompt FROM story_spreads WHERE story_id = $1 ORDER BY spread_number',
        story_id
    )

    print("=== Text-based Character Detection ===")
    from backend.core.types import name_matches_in_text

    for spread in spreads:
        spread_num = spread['spread_number']
        prompt = spread['illustration_prompt'] or ""

        matches = []
        for bible in character_bibles:
            name = bible.get('name', '')
            if name_matches_in_text(name, prompt):
                matches.append(name)

        print(f"Spread {spread_num}: prompt contains '{prompt[:50]}...'")
        print(f"  Matched characters: {matches}")

    await pool.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python diagnose_character_refs.py <story_id>")
        sys.exit(1)

    asyncio.run(diagnose_story(sys.argv[1]))
