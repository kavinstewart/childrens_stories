#!/usr/bin/env python3
"""
Test script to check what contents are being built for illustration.
"""
import asyncio
import asyncpg
import os
import sys
import json
from dotenv import load_dotenv
from PIL import Image
import io

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv('.env')

from backend.core.types import (
    StorySpread, StoryMetadata, CharacterBible, StyleDefinition,
    StoryReferenceSheets, CharacterReferenceSheet
)
from backend.core.modules.spread_illustrator import SpreadIllustrator


async def test_contents_building(story_id: str):
    db_url = os.environ['DATABASE_URL'].replace('postgresql+asyncpg://', 'postgresql://')
    pool = await asyncpg.create_pool(db_url)

    # Get story data
    story = await pool.fetchrow(
        'SELECT title, outline_json FROM stories WHERE id = $1',
        story_id
    )
    print(f"Story: {story['title']}\n")

    # Get character references (bibles and image paths)
    refs = await pool.fetch(
        'SELECT character_name, bible_json, reference_image_path FROM character_references WHERE story_id = $1',
        story_id
    )

    # Build StoryMetadata with character bibles
    outline_data = json.loads(story['outline_json']) if story['outline_json'] else {}

    character_bibles = []
    reference_sheets = StoryReferenceSheets(story_title=story['title'])

    for ref in refs:
        bible_data = json.loads(ref['bible_json']) if ref['bible_json'] else {}
        bible = CharacterBible(
            name=bible_data.get('name', ref['character_name']),
            aliases=bible_data.get('aliases', []),
            species=bible_data.get('species', ''),
            age_appearance=bible_data.get('age_appearance', ''),
            body=bible_data.get('body', ''),
            face=bible_data.get('face', ''),
            hair=bible_data.get('hair', ''),
            eyes=bible_data.get('eyes', ''),
            clothing=bible_data.get('clothing', ''),
        )
        character_bibles.append(bible)

        image_path = ref['reference_image_path']
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            reference_sheets.character_sheets[bible.name] = CharacterReferenceSheet(
                character_name=bible.name,
                reference_image=image_bytes,
                prompt_used="",
                bible=bible,
            )

    print(f"Loaded {len(character_bibles)} character bibles:")
    for bible in character_bibles:
        print(f"  - {bible.name}: aliases={bible.aliases}")
    print(f"\nLoaded {len(reference_sheets.character_sheets)} reference sheets")
    print()

    style_data = outline_data.get('illustration_style', {})
    style = StyleDefinition(
        name=style_data.get('name', 'Default'),
        description=style_data.get('description', ''),
        prompt_prefix=style_data.get('prompt_prefix', ''),
        best_for=style_data.get('best_for', []),
        lighting_direction=style_data.get('lighting_direction', ''),
    )

    outline = StoryMetadata(
        title=story['title'],
        character_bibles=character_bibles,
        illustration_style=style,
    )

    # Get spreads
    spreads_data = await pool.fetch(
        'SELECT spread_number, text, illustration_prompt FROM story_spreads WHERE story_id = $1 ORDER BY spread_number',
        story_id
    )

    # Initialize illustrator (don't actually call API)
    from unittest.mock import patch
    with patch('backend.core.modules.spread_illustrator.get_image_client'):
        with patch('backend.core.modules.spread_illustrator.get_image_model', return_value='test'):
            with patch('backend.core.modules.spread_illustrator.get_image_config', return_value={}):
                illustrator = SpreadIllustrator()

    print("=" * 60)
    print("CONTENTS ANALYSIS FOR EACH SPREAD")
    print("=" * 60)

    for spread_data in spreads_data:
        spread = StorySpread(
            spread_number=spread_data['spread_number'],
            text=spread_data['text'],
            word_count=len(spread_data['text'].split()),
            illustration_prompt=spread_data['illustration_prompt'],
            present_characters=None,  # Simulate missing [Characters:] field
        )

        # Get characters that would be detected
        chars_for_spread = illustrator._get_characters_for_spread(spread, outline)

        # Build prompt
        prompt = illustrator._build_scene_prompt(spread, outline)

        # Build contents
        contents = illustrator._build_contents(spread, outline, reference_sheets, prompt)

        # Count images vs text in contents
        image_count = sum(1 for c in contents if isinstance(c, Image.Image))
        text_count = sum(1 for c in contents if isinstance(c, str))

        print(f"\nSpread {spread.spread_number}:")
        print(f"  Illustration prompt: {spread.illustration_prompt[:60]}...")
        print(f"  Characters detected: {chars_for_spread}")
        print(f"  Contents: {image_count} images, {text_count} text blocks")

        # Show which character references were included
        for i, item in enumerate(contents):
            if isinstance(item, Image.Image):
                print(f"    [Image] size={item.size}")
            elif isinstance(item, str) and "CHARACTER REFERENCE" in item:
                char_name = item.split("CHARACTER REFERENCE for ")[1].split(":")[0] if "CHARACTER REFERENCE for " in item else "?"
                print(f"    [Text] Character reference for: {char_name}")

    await pool.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_contents_building.py <story_id>")
        sys.exit(1)

    asyncio.run(test_contents_building(sys.argv[1]))
