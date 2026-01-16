"""Tests for CharacterBible storage in character_references table.

TDD tests for story-37l6: Store full CharacterBible in database for editing.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.core.types import CharacterBible


class TestCharacterBibleStorage:
    """Test that full CharacterBible is stored and retrieved from database."""

    def test_character_bible_all_fields_serializable(self):
        """CharacterBible with all fields can be serialized to JSON."""
        bible = CharacterBible(
            name="Luna",
            species="girl",
            age_appearance="5 years old",
            body="small and nimble",
            face="round face with rosy cheeks",
            hair="curly red hair in pigtails",
            eyes="bright green eyes",
            clothing="yellow sundress with white flowers",
            signature_item="sparkly magic wand",
            color_palette=["yellow", "green", "red"],
            style_tags=["whimsical", "cheerful"],
        )

        # Convert to dict for JSON serialization
        bible_dict = {
            "name": bible.name,
            "species": bible.species,
            "age_appearance": bible.age_appearance,
            "body": bible.body,
            "face": bible.face,
            "hair": bible.hair,
            "eyes": bible.eyes,
            "clothing": bible.clothing,
            "signature_item": bible.signature_item,
            "color_palette": bible.color_palette,
            "style_tags": bible.style_tags,
        }

        # Should be serializable
        json_str = json.dumps(bible_dict)
        restored = json.loads(json_str)

        assert restored["name"] == "Luna"
        assert restored["hair"] == "curly red hair in pigtails"
        assert restored["eyes"] == "bright green eyes"
        assert restored["clothing"] == "yellow sundress with white flowers"
        assert restored["signature_item"] == "sparkly magic wand"
        assert restored["color_palette"] == ["yellow", "green", "red"]
        assert restored["style_tags"] == ["whimsical", "cheerful"]

    def test_character_bible_to_dict_method(self):
        """CharacterBible.to_dict() returns all fields for storage."""
        bible = CharacterBible(
            name="Max",
            species="dog",
            age_appearance="young puppy",
            body="fluffy golden fur",
            face="friendly face with floppy ears",
            hair="",
            eyes="brown eyes",
            clothing="red collar with bone tag",
            signature_item="tennis ball",
            color_palette=["gold", "red", "brown"],
            style_tags=["playful", "loyal"],
        )

        bible_dict = bible.to_dict()

        assert bible_dict["name"] == "Max"
        assert bible_dict["species"] == "dog"
        assert bible_dict["age_appearance"] == "young puppy"
        assert bible_dict["body"] == "fluffy golden fur"
        assert bible_dict["face"] == "friendly face with floppy ears"
        assert bible_dict["hair"] == ""
        assert bible_dict["eyes"] == "brown eyes"
        assert bible_dict["clothing"] == "red collar with bone tag"
        assert bible_dict["signature_item"] == "tennis ball"
        assert bible_dict["color_palette"] == ["gold", "red", "brown"]
        assert bible_dict["style_tags"] == ["playful", "loyal"]

    def test_character_bible_from_dict_method(self):
        """CharacterBible.from_dict() reconstructs from stored data."""
        stored_data = {
            "name": "Whiskers",
            "species": "cat",
            "age_appearance": "adult cat",
            "body": "sleek grey fur",
            "face": "angular face with white whiskers",
            "hair": "",
            "eyes": "yellow eyes",
            "clothing": "purple bow tie",
            "signature_item": "yarn ball",
            "color_palette": ["grey", "purple", "yellow"],
            "style_tags": ["mysterious", "elegant"],
        }

        bible = CharacterBible.from_dict(stored_data)

        assert bible.name == "Whiskers"
        assert bible.species == "cat"
        assert bible.clothing == "purple bow tie"
        assert bible.signature_item == "yarn ball"
        assert bible.color_palette == ["grey", "purple", "yellow"]
        assert bible.style_tags == ["mysterious", "elegant"]


class TestCharacterReferenceResponse:
    """Test that CharacterReferenceResponse includes bible data."""

    def test_response_includes_bible_fields(self):
        """CharacterReferenceResponse should include full bible data."""
        from backend.api.models.responses import CharacterReferenceResponse

        response = CharacterReferenceResponse(
            character_name="Luna",
            character_description="5 years old, girl, small and nimble, round face with rosy cheeks",
            reference_image_url="/stories/123/characters/Luna/image",
            bible={
                "name": "Luna",
                "species": "girl",
                "age_appearance": "5 years old",
                "body": "small and nimble",
                "face": "round face with rosy cheeks",
                "hair": "curly red hair in pigtails",
                "eyes": "bright green eyes",
                "clothing": "yellow sundress with white flowers",
                "signature_item": "sparkly magic wand",
                "color_palette": ["yellow", "green", "red"],
                "style_tags": ["whimsical", "cheerful"],
            },
        )

        assert response.bible is not None
        assert response.bible["hair"] == "curly red hair in pigtails"
        assert response.bible["signature_item"] == "sparkly magic wand"
        assert response.bible["color_palette"] == ["yellow", "green", "red"]


class TestStoryGenerationCharacterBibleStorage:
    """Test that story generation saves full CharacterBible."""

    def test_char_refs_data_includes_bible_json(self):
        """Character refs data prepared for save includes bible_json."""
        # This tests the structure we expect story_generation.py to produce
        from backend.core.types import (
            CharacterBible,
            CharacterReferenceSheet,
            StoryReferenceSheets,
        )

        # Create a character bible
        bible = CharacterBible(
            name="Luna",
            species="girl",
            age_appearance="5 years old",
            body="small and nimble",
            face="round face with rosy cheeks",
            hair="curly red hair in pigtails",
            eyes="bright green eyes",
            clothing="yellow sundress with white flowers",
            signature_item="sparkly magic wand",
            color_palette=["yellow", "green", "red"],
            style_tags=["whimsical", "cheerful"],
        )

        # Create reference sheet (as would be generated)
        sheet = CharacterReferenceSheet(
            character_name="Luna",
            reference_image=b"fake image data",
            prompt_used="test prompt",
            character_description="5 years old, girl, small and nimble, round face with rosy cheeks",
        )
        # Attach bible to sheet for storage
        sheet.bible = bible

        # Verify bible is attached
        assert sheet.bible is not None
        assert sheet.bible.hair == "curly red hair in pigtails"
        assert sheet.bible.signature_item == "sparkly magic wand"


class TestRepositoryCharacterBibleStorage:
    """Test repository stores and retrieves bible_json."""

    @pytest.mark.asyncio
    async def test_save_completed_story_includes_bible_json(self):
        """Repository.save_completed_story stores bible_json for each character."""
        from backend.api.database.repository import StoryRepository

        # Create mock connection
        conn = MagicMock()
        conn.execute = AsyncMock()
        conn.executemany = AsyncMock()
        conn.transaction = MagicMock()
        conn.transaction.return_value.__aenter__ = AsyncMock()
        conn.transaction.return_value.__aexit__ = AsyncMock()

        repo = StoryRepository(conn)

        # Character refs with bible_json
        char_refs = [
            {
                "character_name": "Luna",
                "character_description": "5 years old, girl",
                "reference_image_path": "/path/to/luna.png",
                "bible_json": json.dumps({
                    "name": "Luna",
                    "species": "girl",
                    "age_appearance": "5 years old",
                    "body": "small and nimble",
                    "face": "round face",
                    "hair": "curly red hair",
                    "eyes": "green eyes",
                    "clothing": "yellow sundress",
                    "signature_item": "magic wand",
                    "color_palette": ["yellow", "green"],
                    "style_tags": ["whimsical"],
                }),
            }
        ]

        await repo.save_completed_story(
            story_id="test-story-id",
            title="Test Story",
            word_count=100,
            spread_count=3,
            attempts=1,
            is_illustrated=True,
            outline_json="{}",
            judgment_json=None,
            spreads=[],
            character_refs=char_refs,
        )

        # Verify executemany was called with bible_json in the insert
        calls = conn.executemany.call_args_list
        char_ref_call = [c for c in calls if "character_references" in str(c)]
        assert len(char_ref_call) == 1

        # The SQL should include bible_json column
        sql = char_ref_call[0][0][0]
        assert "bible_json" in sql

        # The data should include bible_json
        data = char_ref_call[0][0][1]
        assert len(data) == 1
        # Data is a tuple: (story_id, character_name, character_description, reference_image_path, bible_json)
        assert len(data[0]) == 5
        assert "Luna" in data[0][4]  # bible_json contains the character name

    @pytest.mark.asyncio
    async def test_get_story_returns_bible_data(self):
        """Repository.get_story returns bible data in character references."""
        from backend.api.database.repository import StoryRepository
        import asyncpg
        from uuid import UUID

        # Create mock connection with story and character data
        conn = MagicMock()

        test_uuid = UUID("12345678-1234-5678-1234-567812345678")

        # Mock story record
        story_record = {
            "id": test_uuid,
            "status": "completed",
            "goal": "test goal",
            "target_age_range": "4-7",
            "generation_type": "illustrated",
            "llm_model": "test-model",
            "created_at": None,
            "started_at": None,
            "completed_at": None,
            "title": "Test Story",
            "word_count": 100,
            "spread_count": 3,
            "attempts": 1,
            "outline_json": '{"title": "Test Story", "setting": "forest"}',
            "judgment_json": None,
            "progress_json": None,
            "error_message": None,
        }

        # Mock character reference with bible_json
        char_ref_record = {
            "character_name": "Luna",
            "character_description": "5 years old, girl",
            "reference_image_path": "/path/to/luna.png",
            "bible_json": json.dumps({
                "name": "Luna",
                "species": "girl",
                "hair": "curly red hair",
                "signature_item": "magic wand",
            }),
        }

        conn.fetchrow = AsyncMock(return_value=story_record)
        conn.fetch = AsyncMock(side_effect=[
            [],  # spreads
            [char_ref_record],  # character_references
        ])

        repo = StoryRepository(conn)
        response = await repo.get_story(str(test_uuid))

        assert response is not None
        assert response.character_references is not None
        assert len(response.character_references) == 1

        char_ref = response.character_references[0]
        assert char_ref.character_name == "Luna"
        assert char_ref.bible is not None
        assert char_ref.bible["hair"] == "curly red hair"
        assert char_ref.bible["signature_item"] == "magic wand"
