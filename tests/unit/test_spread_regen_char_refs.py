"""Unit tests for spread regeneration character reference loading.

These tests verify:
1. story-cd55: Entity ID to filename matching (@e1 -> _e1_reference.png)
2. story-95zk: Character bibles are populated in StoryMetadata during regeneration
3. story-huqf: No text-based fallback - returns empty list when no explicit entity data
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


TEST_STORY_ID = "12345678-1234-5678-1234-567812345678"
TEST_JOB_ID = "regen123"


class TestLoadCharacterRefsFilenameMatching:
    """Tests for _load_character_refs filename matching (story-cd55).

    Bug: Character names in DB use @ prefix (@e1, @e2) but reference image
    files use _ prefix (_e1_reference.png). The matching logic failed because
    '@e1' is not found in '_e1_reference'.
    """

    @pytest.mark.asyncio
    async def test_load_character_refs_matches_at_prefix_to_underscore_filename(self, tmp_path):
        """Character names with @ prefix should match files with _ prefix."""
        from backend.api.services.spread_regeneration import _load_character_refs

        # Set up directory structure: story_id/character_refs/_e1_reference.png
        story_dir = tmp_path / TEST_STORY_ID
        refs_dir = story_dir / "character_refs"
        refs_dir.mkdir(parents=True)

        # Create a fake reference image file
        ref_image_path = refs_dir / "_e1_reference.png"
        fake_image_bytes = b"fake_png_data_for_lion_character"
        ref_image_path.write_bytes(fake_image_bytes)

        # Create mock story with character reference using @e1 naming
        mock_story = MagicMock()
        mock_char_ref = MagicMock()
        mock_char_ref.character_name = "@e1"  # DB stores with @ prefix
        mock_char_ref.character_description = "A brave lion"
        mock_story.character_references = [mock_char_ref]
        mock_story.metadata = MagicMock()
        mock_story.metadata.title = "Lion Story"

        # Patch STORIES_DIR to use our temp directory
        with patch("backend.api.services.spread_regeneration.STORIES_DIR", tmp_path):
            result = await _load_character_refs(TEST_STORY_ID, mock_story)

        # Should find and load the character reference
        assert result is not None, "Should have loaded character refs"
        assert "@e1" in result.character_sheets, "Should have @e1 in character_sheets"
        assert result.character_sheets["@e1"].reference_image == fake_image_bytes

    @pytest.mark.asyncio
    async def test_load_character_refs_matches_multiple_entities(self, tmp_path):
        """Multiple entity IDs should all match their corresponding files."""
        from backend.api.services.spread_regeneration import _load_character_refs

        # Set up directory structure
        story_dir = tmp_path / TEST_STORY_ID
        refs_dir = story_dir / "character_refs"
        refs_dir.mkdir(parents=True)

        # Create multiple reference images
        (refs_dir / "_e1_reference.png").write_bytes(b"lion_image")
        (refs_dir / "_e2_reference.png").write_bytes(b"friend_image")
        (refs_dir / "_e4_reference.png").write_bytes(b"elephant_image")

        # Create mock story with multiple character references
        mock_story = MagicMock()
        mock_refs = []
        for entity_id, desc in [("@e1", "Lion"), ("@e2", "Friend"), ("@e4", "Elephant")]:
            mock_ref = MagicMock()
            mock_ref.character_name = entity_id
            mock_ref.character_description = desc
            mock_refs.append(mock_ref)
        mock_story.character_references = mock_refs
        mock_story.metadata = MagicMock()
        mock_story.metadata.title = "Multi Character Story"

        with patch("backend.api.services.spread_regeneration.STORIES_DIR", tmp_path):
            result = await _load_character_refs(TEST_STORY_ID, mock_story)

        assert result is not None
        assert len(result.character_sheets) == 3
        assert "@e1" in result.character_sheets
        assert "@e2" in result.character_sheets
        assert "@e4" in result.character_sheets
        assert result.character_sheets["@e1"].reference_image == b"lion_image"
        assert result.character_sheets["@e2"].reference_image == b"friend_image"
        assert result.character_sheets["@e4"].reference_image == b"elephant_image"

    @pytest.mark.asyncio
    async def test_load_character_refs_handles_missing_file(self, tmp_path):
        """Characters without reference files should be skipped gracefully."""
        from backend.api.services.spread_regeneration import _load_character_refs

        story_dir = tmp_path / TEST_STORY_ID
        refs_dir = story_dir / "character_refs"
        refs_dir.mkdir(parents=True)

        # Only create file for @e1, not for @e2
        (refs_dir / "_e1_reference.png").write_bytes(b"lion_image")

        mock_story = MagicMock()
        mock_refs = []
        for entity_id in ["@e1", "@e2"]:  # @e2 has no file
            mock_ref = MagicMock()
            mock_ref.character_name = entity_id
            mock_ref.character_description = f"Character {entity_id}"
            mock_refs.append(mock_ref)
        mock_story.character_references = mock_refs
        mock_story.metadata = MagicMock()
        mock_story.metadata.title = "Test"

        with patch("backend.api.services.spread_regeneration.STORIES_DIR", tmp_path):
            result = await _load_character_refs(TEST_STORY_ID, mock_story)

        # Should still load the one that exists
        assert result is not None
        assert "@e1" in result.character_sheets
        assert "@e2" not in result.character_sheets


class TestRegenerateSpreadCharacterBibles:
    """Tests for character bible population in regenerate_spread (story-95zk).

    Bug: StoryMetadata was built without character_bibles, breaking
    _get_characters_for_spread() which needs entity_bibles to determine
    which characters appear in each spread.
    """

    def _create_mock_pool_and_conn(self):
        """Create a properly mocked asyncpg pool and connection."""
        from contextlib import asynccontextmanager

        mock_conn = AsyncMock()
        mock_pool = MagicMock()

        @asynccontextmanager
        async def mock_acquire():
            yield mock_conn

        mock_pool.acquire = mock_acquire
        mock_pool.close = AsyncMock()

        return mock_pool, mock_conn

    def _create_mock_story_with_bibles(self):
        """Create a mock story with character_references containing bible_json."""
        mock_story = MagicMock()
        mock_story.metadata = MagicMock()
        mock_story.metadata.title = "Lion Story"

        # Create a proper StyleDefinition mock
        mock_story.metadata.illustration_style = MagicMock()
        mock_story.metadata.illustration_style.name = "Watercolor"
        mock_story.metadata.illustration_style.description = "Soft watercolor"
        mock_story.metadata.illustration_style.prompt_prefix = "watercolor style"
        mock_story.metadata.illustration_style.best_for = ["animals"]
        mock_story.metadata.illustration_style.lighting_direction = "soft light"

        # Character references with bible_json
        mock_char_ref = MagicMock()
        mock_char_ref.character_name = "@e1"
        mock_char_ref.character_description = "A brave lion"
        mock_char_ref.bible = {
            "name": "Leo the Lion",
            "species": "lion",
            "age_appearance": "adult",
            "body": "muscular",
            "face": "friendly",
            "hair": "golden mane",
            "eyes": "amber",
            "clothing": "none",
            "signature_item": "red scarf",
        }

        mock_char_ref2 = MagicMock()
        mock_char_ref2.character_name = "@e2"
        mock_char_ref2.character_description = "A small mouse"
        mock_char_ref2.bible = {
            "name": "Max the Mouse",
            "species": "mouse",
            "age_appearance": "young",
            "body": "tiny",
            "face": "curious",
        }

        mock_story.character_references = [mock_char_ref, mock_char_ref2]

        return mock_story

    @pytest.mark.asyncio
    async def test_regenerate_spread_populates_entity_bibles_in_metadata(self):
        """Regeneration should populate entity_bibles from character_references."""
        from backend.api.services.spread_regeneration import regenerate_spread

        mock_pool, mock_conn = self._create_mock_pool_and_conn()
        mock_story = self._create_mock_story_with_bibles()

        captured_metadata = None

        def capture_illustrate_call(*args, **kwargs):
            nonlocal captured_metadata
            captured_metadata = kwargs.get("outline")
            return b"fake_image"

        with patch("backend.api.services.spread_regeneration.asyncpg") as mock_asyncpg, \
             patch("backend.api.services.spread_regeneration.StoryRepository") as mock_repo_class, \
             patch("backend.api.services.spread_regeneration.SpreadRegenJobRepository") as mock_regen_repo_class, \
             patch("backend.core.modules.spread_illustrator.SpreadIllustrator") as mock_illustrator_class, \
             patch("backend.api.services.spread_regeneration._load_character_refs") as mock_load_refs, \
             patch("backend.api.services.spread_regeneration._save_image_atomically") as mock_save:

            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_story = AsyncMock(return_value=mock_story)

            mock_regen_repo = AsyncMock()
            mock_regen_repo_class.return_value = mock_regen_repo
            mock_regen_repo.get_spread = AsyncMock(return_value={
                "spread_number": 5,
                "text": "Leo roared loudly.",
                "word_count": 3,
                "illustration_prompt": "A lion roaring",
            })

            mock_load_refs.return_value = None
            mock_save.return_value = None

            mock_illustrator = MagicMock()
            mock_illustrator.illustrate_spread.side_effect = capture_illustrate_call
            mock_illustrator_class.return_value = mock_illustrator

            await regenerate_spread(TEST_JOB_ID, TEST_STORY_ID, 5)

            # Verify entity_bibles was populated in StoryMetadata
            assert captured_metadata is not None, "Should have captured metadata"
            assert captured_metadata.entity_bibles, "entity_bibles should be populated"
            assert "@e1" in captured_metadata.entity_bibles, "Should have @e1 in entity_bibles"
            assert "@e2" in captured_metadata.entity_bibles, "Should have @e2 in entity_bibles"

            # Verify the bible content
            e1_bible = captured_metadata.entity_bibles["@e1"]
            assert e1_bible.name == "Leo the Lion"
            assert e1_bible.species == "lion"

    @pytest.mark.asyncio
    async def test_regenerate_spread_handles_missing_bible(self):
        """Characters without bible_json should be handled gracefully."""
        from backend.api.services.spread_regeneration import regenerate_spread

        mock_pool, mock_conn = self._create_mock_pool_and_conn()

        # Create story where one character has no bible
        mock_story = MagicMock()
        mock_story.metadata = MagicMock()
        mock_story.metadata.title = "Test Story"
        mock_story.metadata.illustration_style = None  # No style

        mock_char_ref = MagicMock()
        mock_char_ref.character_name = "@e1"
        mock_char_ref.character_description = "A lion"
        mock_char_ref.bible = None  # No bible

        mock_story.character_references = [mock_char_ref]

        captured_metadata = None

        def capture_illustrate_call(*args, **kwargs):
            nonlocal captured_metadata
            captured_metadata = kwargs.get("outline")
            return b"fake_image"

        with patch("backend.api.services.spread_regeneration.asyncpg") as mock_asyncpg, \
             patch("backend.api.services.spread_regeneration.StoryRepository") as mock_repo_class, \
             patch("backend.api.services.spread_regeneration.SpreadRegenJobRepository") as mock_regen_repo_class, \
             patch("backend.core.modules.spread_illustrator.SpreadIllustrator") as mock_illustrator_class, \
             patch("backend.api.services.spread_regeneration._load_character_refs") as mock_load_refs, \
             patch("backend.api.services.spread_regeneration._save_image_atomically") as mock_save:

            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_story = AsyncMock(return_value=mock_story)

            mock_regen_repo = AsyncMock()
            mock_regen_repo_class.return_value = mock_regen_repo
            mock_regen_repo.get_spread = AsyncMock(return_value={
                "spread_number": 1,
                "text": "Text",
                "word_count": 1,
                "illustration_prompt": "Prompt",
            })

            mock_load_refs.return_value = None
            mock_save.return_value = None

            mock_illustrator = MagicMock()
            mock_illustrator.illustrate_spread.side_effect = capture_illustrate_call
            mock_illustrator_class.return_value = mock_illustrator

            await regenerate_spread(TEST_JOB_ID, TEST_STORY_ID, 1)

            # Should not crash, entity_bibles should be empty
            assert captured_metadata is not None
            # @e1 should not be in entity_bibles since it had no bible
            assert "@e1" not in captured_metadata.entity_bibles


class TestGetCharactersForSpreadNoFallback:
    """Tests for _get_characters_for_spread after text-based fallback removal (story-huqf).

    The text-based fallback was removed because it caused issues with settings/locations
    (e.g., "womb" in shark story) that don't appear literally in text. With present_entity_ids
    now persisted (story-v0qr), spreads without explicit entity data return an empty list.
    """

    def test_returns_empty_when_present_entity_ids_is_none(self):
        """When present_entity_ids is None, should return empty list (no text-based fallback)."""
        from backend.core.modules.spread_illustrator import SpreadIllustrator
        from backend.core.types import StorySpread, StoryMetadata, EntityBible

        illustrator = SpreadIllustrator()

        # Create spread WITHOUT present_entity_ids
        spread = StorySpread(
            spread_number=10,
            text="Leo sat quietly. Mama Lion looked at him.",
            word_count=7,
            illustration_prompt="A lion cub sitting with adult lioness",
            present_entity_ids=None,  # Not set
            present_characters=None,
        )

        # Create metadata with entity_bibles (new format)
        metadata = StoryMetadata(
            title="Lion Story",
            entity_bibles={
                "@e1": EntityBible(name="Leo", species="lion cub"),
                "@e2": EntityBible(name="Mama Lion", species="adult lioness"),
                "@e3": EntityBible(name="The Zebras", species="zebra"),
            },
            character_bibles=[],  # Empty - legacy format not used
        )

        # Call the method directly
        result = illustrator._get_characters_for_spread(spread, metadata)

        # Should return empty list - no text-based fallback
        assert result == [], "Should return empty list without text-based fallback"

    def test_returns_empty_when_no_explicit_entity_data(self):
        """Should return empty list when no entity data is provided."""
        from backend.core.modules.spread_illustrator import SpreadIllustrator
        from backend.core.types import StorySpread, StoryMetadata, EntityBible

        illustrator = SpreadIllustrator()

        spread = StorySpread(
            spread_number=1,
            text="The sun set over the savannah.",
            word_count=6,
            illustration_prompt="A sunset over grasslands",
            present_entity_ids=None,
            present_characters=None,
        )

        metadata = StoryMetadata(
            title="Lion Story",
            entity_bibles={
                "@e1": EntityBible(name="Leo", species="lion"),
                "@e2": EntityBible(name="Mama Lion", species="lioness"),
            },
        )

        result = illustrator._get_characters_for_spread(spread, metadata)

        assert result == [], "Should return empty list when no explicit entity data"

    def test_no_text_based_matching_even_with_names_in_prompt(self):
        """Should NOT do text-based matching even if names appear in illustration_prompt."""
        from backend.core.modules.spread_illustrator import SpreadIllustrator
        from backend.core.types import StorySpread, StoryMetadata, EntityBible

        illustrator = SpreadIllustrator()

        spread = StorySpread(
            spread_number=5,
            text="The dust settled.",  # No character names here
            word_count=3,
            illustration_prompt="Leo looking sad in the grass",  # Leo IS here
            present_entity_ids=None,  # But no explicit entity IDs
            present_characters=None,
        )

        metadata = StoryMetadata(
            title="Lion Story",
            entity_bibles={
                "@e1": EntityBible(name="Leo", species="lion"),
            },
        )

        result = illustrator._get_characters_for_spread(spread, metadata)

        # Should NOT find Leo because we don't do text-based fallback
        assert result == [], "Should NOT do text-based matching"

    def test_uses_present_entity_ids_when_available(self):
        """When present_entity_ids is set, should use it directly (no fallback)."""
        from backend.core.modules.spread_illustrator import SpreadIllustrator
        from backend.core.types import StorySpread, StoryMetadata, EntityBible

        illustrator = SpreadIllustrator()

        spread = StorySpread(
            spread_number=5,
            text="Leo and Mama Lion and The Zebras all together.",
            word_count=8,
            illustration_prompt="All characters together",
            present_entity_ids=["@e1"],  # Only Leo specified
            present_characters=None,
        )

        metadata = StoryMetadata(
            title="Lion Story",
            entity_bibles={
                "@e1": EntityBible(name="Leo", species="lion"),
                "@e2": EntityBible(name="Mama Lion", species="lioness"),
                "@e3": EntityBible(name="The Zebras", species="zebra"),
            },
        )

        result = illustrator._get_characters_for_spread(spread, metadata)

        # Should only return what's in present_entity_ids, not all mentioned
        assert result == ["@e1"], "Should use present_entity_ids directly"

    def test_legacy_stories_without_present_characters_return_empty(self):
        """Legacy stories without present_characters should return empty list.

        With text-based fallback removed (story-huqf), legacy stories that have
        neither present_entity_ids nor present_characters will not get character
        references. This is preferable to unreliable text-based guessing.
        """
        from backend.core.modules.spread_illustrator import SpreadIllustrator
        from backend.core.types import StorySpread, StoryMetadata, EntityBible

        illustrator = SpreadIllustrator()

        spread = StorySpread(
            spread_number=5,
            text="Crow flew over Otto's head.",
            word_count=5,
            illustration_prompt="A crow flying over an otter",
            present_entity_ids=None,  # No entity IDs
            present_characters=None,  # No legacy character list
        )

        metadata = StoryMetadata(
            title="Old Story",
            entity_bibles={},  # Empty - old story
            character_bibles=[
                EntityBible(name="Crow", species="crow"),
                EntityBible(name="Otto", species="otter"),
                EntityBible(name="Fox", species="fox"),
            ],
        )

        result = illustrator._get_characters_for_spread(spread, metadata)

        # Should return empty list - no text-based fallback
        assert result == [], "Should return empty without text-based fallback"
