"""
Tests for character alias extraction and matching.

These tests verify that:
1. CharacterBible can store aliases
2. Name matching considers aliases when looking up characters
3. CharacterExtractor extracts name variants/aliases from stories

This addresses the bug where LLM outputs "George Washington" in [Characters:]
but CharacterExtractor names the bible "George", causing reference lookup to fail.
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.core.types import (
    CharacterBible,
    StoryMetadata,
    StoryReferenceSheets,
    CharacterReferenceSheet,
    StyleDefinition,
    _names_match,
    build_character_lookup,
)
from backend.core.modules.character_extractor import CharacterExtractor, ExtractedCharacter


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_style():
    """An illustration style for testing."""
    return StyleDefinition(
        name="Watercolor",
        description="Soft watercolor style",
        prompt_prefix="Watercolor children's book illustration",
        best_for=["nature"],
        lighting_direction="soft daylight",
    )


@pytest.fixture
def george_washington_bible():
    """A character bible with aliases for George Washington."""
    return CharacterBible(
        name="George",
        species="human",
        age_appearance="young boy",
        body="small child",
        face="round cheeks, curious eyes",
        hair="brown, short",
        clothing="colonial-era clothing",
        aliases=["George Washington", "President Washington", "General Washington"],
    )


@pytest.fixture
def outline_with_aliases(sample_style, george_washington_bible):
    """Story metadata with characters that have aliases."""
    return StoryMetadata(
        title="The Big Chair",
        character_bibles=[
            george_washington_bible,
            CharacterBible(
                name="The Eagle",
                species="bald eagle",
                age_appearance="adult",
                body="large wingspan, white head",
                aliases=["Eagle", "Mr. Eagle", "the great eagle"],
            ),
        ],
        illustration_style=sample_style,
    )


@pytest.fixture
def reference_sheets_with_aliases(george_washington_bible):
    """Reference sheets with characters that have aliases."""
    sheets = StoryReferenceSheets(story_title="The Big Chair")
    sheets.character_sheets["George"] = CharacterReferenceSheet(
        character_name="George",
        reference_image=b"fake_image_bytes",
        prompt_used="test prompt",
        bible=george_washington_bible,
    )
    sheets.character_sheets["The Eagle"] = CharacterReferenceSheet(
        character_name="The Eagle",
        reference_image=b"fake_eagle_bytes",
        prompt_used="eagle prompt",
        bible=CharacterBible(
            name="The Eagle",
            species="bald eagle",
            aliases=["Eagle", "Mr. Eagle"],
        ),
    )
    return sheets


# =============================================================================
# Test 1: CharacterBible with Aliases
# =============================================================================

class TestCharacterBibleAliases:
    """Tests for CharacterBible alias storage and serialization."""

    def test_character_bible_has_aliases_field(self):
        """CharacterBible should have an aliases field."""
        bible = CharacterBible(
            name="George",
            aliases=["George Washington", "President Washington"],
        )
        assert hasattr(bible, "aliases")
        assert bible.aliases == ["George Washington", "President Washington"]

    def test_character_bible_aliases_default_empty(self):
        """CharacterBible aliases should default to empty list."""
        bible = CharacterBible(name="George")
        assert bible.aliases == []

    def test_character_bible_to_dict_includes_aliases(self):
        """to_dict() should include aliases."""
        bible = CharacterBible(
            name="George",
            aliases=["George Washington"],
        )
        d = bible.to_dict()
        assert "aliases" in d
        assert d["aliases"] == ["George Washington"]

    def test_character_bible_from_dict_loads_aliases(self):
        """from_dict() should load aliases."""
        data = {
            "name": "George",
            "aliases": ["George Washington", "President Washington"],
        }
        bible = CharacterBible.from_dict(data)
        assert bible.aliases == ["George Washington", "President Washington"]

    def test_character_bible_from_dict_without_aliases(self):
        """from_dict() should handle missing aliases gracefully."""
        data = {"name": "George"}
        bible = CharacterBible.from_dict(data)
        assert bible.aliases == []


# =============================================================================
# Test 2: _names_match with Aliases
# =============================================================================

class TestNamesMatchWithAliases:
    """Tests for _names_match function with alias support."""

    def test_names_match_exact_still_works(self):
        """Exact matching should still work."""
        assert _names_match("George", "George")
        assert _names_match("The Eagle", "The Eagle")

    def test_names_match_alias_exact(self):
        """Query matching an alias exactly should return True."""
        aliases = ["George Washington", "President Washington"]
        assert _names_match("George Washington", "George", aliases=aliases)
        assert _names_match("President Washington", "George", aliases=aliases)

    def test_names_match_alias_case_insensitive(self):
        """Alias matching should be case-insensitive."""
        aliases = ["George Washington"]
        assert _names_match("george washington", "George", aliases=aliases)
        assert _names_match("GEORGE WASHINGTON", "George", aliases=aliases)

    def test_names_match_alias_normalized(self):
        """Alias matching should normalize whitespace."""
        aliases = ["George  Washington"]  # Extra space
        assert _names_match("George Washington", "George", aliases=aliases)

    def test_names_match_no_alias_no_match(self):
        """Without aliases, partial names should not match."""
        # This is the bug scenario - should NOT match without aliases
        assert not _names_match("George Washington", "George")
        assert not _names_match("President Washington", "George")

    def test_names_match_empty_aliases(self):
        """Empty aliases list should not change behavior."""
        assert not _names_match("George Washington", "George", aliases=[])

    def test_names_match_none_aliases(self):
        """None aliases should be handled gracefully."""
        assert not _names_match("George Washington", "George", aliases=None)


# =============================================================================
# Test 3: build_character_lookup with Aliases
# =============================================================================

class TestBuildCharacterLookupWithAliases:
    """Tests for build_character_lookup function with alias support."""

    def test_build_lookup_includes_aliases(self, george_washington_bible):
        """build_character_lookup should include aliases in the lookup dict."""
        bibles = [george_washington_bible]
        lookup = build_character_lookup(bibles)

        # Canonical name should map to itself
        assert lookup["george"] == "George"

        # Aliases should map to canonical name
        assert lookup["george washington"] == "George"
        assert lookup["president washington"] == "George"
        assert lookup["general washington"] == "George"

    def test_build_lookup_normalizes_aliases(self, george_washington_bible):
        """Aliases in lookup should be normalized."""
        bibles = [george_washington_bible]
        lookup = build_character_lookup(bibles)

        # Should be able to look up with any case
        assert "george washington" in lookup
        # Original case shouldn't matter for normalized lookup
        assert lookup.get("george washington") == "George"

    def test_build_lookup_without_aliases(self):
        """Characters without aliases should still work."""
        bible = CharacterBible(name="Clank")
        lookup = build_character_lookup([bible])
        assert lookup["clank"] == "Clank"


# =============================================================================
# Test 4: StoryMetadata.get_character_bible with Aliases
# =============================================================================

class TestGetCharacterBibleWithAliases:
    """Tests for get_character_bible method with alias support."""

    def test_get_bible_by_canonical_name(self, outline_with_aliases):
        """Should find bible by canonical name."""
        bible = outline_with_aliases.get_character_bible("George")
        assert bible is not None
        assert bible.name == "George"

    def test_get_bible_by_alias(self, outline_with_aliases):
        """Should find bible by alias name."""
        bible = outline_with_aliases.get_character_bible("George Washington")
        assert bible is not None
        assert bible.name == "George"

    def test_get_bible_by_alias_case_insensitive(self, outline_with_aliases):
        """Alias lookup should be case-insensitive."""
        bible = outline_with_aliases.get_character_bible("GEORGE WASHINGTON")
        assert bible is not None
        assert bible.name == "George"

    def test_get_bible_article_stripped_alias(self, outline_with_aliases):
        """Should handle article-stripped aliases."""
        # "The Eagle" has alias "Eagle"
        bible = outline_with_aliases.get_character_bible("Eagle")
        assert bible is not None
        assert bible.name == "The Eagle"


# =============================================================================
# Test 5: StoryReferenceSheets.get_sheet with Aliases
# =============================================================================

class TestGetSheetWithAliases:
    """Tests for get_sheet method with alias support."""

    def test_get_sheet_by_canonical_name(self, reference_sheets_with_aliases):
        """Should find sheet by canonical name."""
        sheet = reference_sheets_with_aliases.get_sheet("George")
        assert sheet is not None
        assert sheet.character_name == "George"

    def test_get_sheet_by_alias(self, reference_sheets_with_aliases):
        """Should find sheet by alias name."""
        sheet = reference_sheets_with_aliases.get_sheet("George Washington")
        assert sheet is not None
        assert sheet.character_name == "George"

    def test_get_sheet_by_alias_case_insensitive(self, reference_sheets_with_aliases):
        """Alias lookup should be case-insensitive."""
        sheet = reference_sheets_with_aliases.get_sheet("george washington")
        assert sheet is not None
        assert sheet.character_name == "George"

    def test_get_sheet_returns_none_for_unknown(self, reference_sheets_with_aliases):
        """Should return None for unknown names."""
        sheet = reference_sheets_with_aliases.get_sheet("Unknown Character")
        assert sheet is None


# =============================================================================
# Test 6: CharacterExtractor Alias Extraction
# =============================================================================

class TestCharacterExtractorAliases:
    """Tests for CharacterExtractor extracting aliases from stories."""

    def test_extracted_character_has_aliases(self):
        """ExtractedCharacter should have aliases field."""
        char = ExtractedCharacter(
            name="George",
            details="a young boy",
            aliases=["George Washington", "President Washington"],
        )
        assert char.aliases == ["George Washington", "President Washington"]

    def test_extracted_character_aliases_default_empty(self):
        """ExtractedCharacter aliases should default to empty list."""
        char = ExtractedCharacter(name="George", details="a young boy")
        assert char.aliases == []

    def test_parse_characters_with_aliases(self):
        """_parse_characters should extract aliases from formatted output."""
        extractor = CharacterExtractor()

        raw_output = """
NAME: George | ALIASES: George Washington, President Washington | DETAILS: a young boy who dreams of adventure
NAME: Eagle | ALIASES: The Eagle, Mr. Eagle | DETAILS: a wise bald eagle who guides George
"""
        characters = extractor._parse_characters(raw_output)

        assert len(characters) == 2

        george = next(c for c in characters if c.name == "George")
        assert "George Washington" in george.aliases
        assert "President Washington" in george.aliases

        eagle = next(c for c in characters if c.name == "Eagle")
        assert "The Eagle" in eagle.aliases
        assert "Mr. Eagle" in eagle.aliases

    def test_parse_characters_without_aliases(self):
        """_parse_characters should handle output without aliases."""
        extractor = CharacterExtractor()

        # Old format without aliases should still work
        raw_output = "NAME: George | DETAILS: a young boy"
        characters = extractor._parse_characters(raw_output)

        assert len(characters) == 1
        assert characters[0].name == "George"
        assert characters[0].aliases == []


# =============================================================================
# Test 7: Integration - Full Pipeline
# =============================================================================

class TestAliasIntegration:
    """Integration tests for alias functionality in the full pipeline."""

    def test_spread_illustrator_finds_characters_by_alias(
        self, outline_with_aliases, reference_sheets_with_aliases
    ):
        """SpreadIllustrator should find character references using aliases."""
        from backend.core.types import StorySpread
        from backend.core.modules.spread_illustrator import SpreadIllustrator

        # Mock the image generation
        with patch.object(SpreadIllustrator, '_generate_image', return_value=b'image'):
            with patch('backend.core.modules.spread_illustrator.get_image_client'):
                with patch('backend.core.modules.spread_illustrator.get_image_model', return_value='test'):
                    with patch('backend.core.modules.spread_illustrator.get_image_config', return_value={}):
                        illustrator = SpreadIllustrator()

                        spread = StorySpread(
                            spread_number=1,
                            text="George Washington sat in the big chair.",
                            word_count=7,
                            illustration_prompt="A young boy sitting in a large chair",
                            present_characters=["George Washington"],  # LLM uses full name
                        )

                        # _resolve_present_characters should find "George" via alias
                        resolved = illustrator._resolve_present_characters(
                            spread.present_characters,
                            outline_with_aliases.character_bibles
                        )

                        assert "George" in resolved
