"""
Regression tests for character selection in spread illustration.

These tests ensure we don't reintroduce substring-based matching bugs
that caused false positives like "He" matching "The Blue Bird".
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.core.modules.spread_illustrator import SpreadIllustrator, STOPWORDS
from backend.core.types import (
    StorySpread,
    StoryMetadata,
    CharacterBible,
    StyleDefinition,
    StoryReferenceSheets,
    CharacterReferenceSheet,
    _names_match,
    _normalize_name,
    _strip_leading_article,
)


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
def clank_and_friends_outline(sample_style):
    """
    Outline for "Clank and the Green Thing" story.

    Characters:
    - Clank (a robot, no article)
    - The Blue Bird (has leading "The")
    - The Green Thing (has leading "The")

    This is the exact scenario from the bug report.
    """
    return StoryMetadata(
        title="Clank and the Green Thing",
        setting="A forest clearing",
        character_bibles=[
            CharacterBible(
                name="Clank",
                species="robot",
                age_appearance="ageless",
                body="metal",
                face="LED screen",
            ),
            CharacterBible(
                name="The Blue Bird",
                species="bird",
                age_appearance="young",
                body="small blue feathers",
                face="beak",
            ),
            CharacterBible(
                name="The Green Thing",
                species="mysterious creature",
                age_appearance="unknown",
                body="amorphous green blob",
                face="none",
            ),
        ],
        illustration_style=sample_style,
    )


@pytest.fixture
def mock_image_client():
    """Mock Google genai client."""
    client = MagicMock()
    fake_part = MagicMock()
    fake_part.inline_data = MagicMock()
    fake_part.inline_data.data = b"generated image bytes"
    fake_response = MagicMock()
    fake_response.candidates = [MagicMock()]
    fake_response.candidates[0].content.parts = [fake_part]
    client.models.generate_content.return_value = fake_response
    return client


@pytest.fixture
def illustrator(mock_image_client):
    """SpreadIllustrator with mocked client."""
    with patch('backend.core.modules.spread_illustrator.get_image_client', return_value=mock_image_client):
        with patch('backend.core.modules.spread_illustrator.get_image_model', return_value='test-model'):
            with patch('backend.core.modules.spread_illustrator.get_image_config', return_value={}):
                yield SpreadIllustrator()


# =============================================================================
# Test 1: False Positive Reproduction (Bug Regression Test)
# =============================================================================

class TestFalsePositivePrevention:
    """
    Tests that verify the substring matching bug is fixed.

    The bug: "He" was matching "The Blue Bird" because "he" is in "the".
    """

    def test_he_does_not_match_the_blue_bird(self, illustrator, clank_and_friends_outline):
        """
        Spread with text 'He walked alone.' should NOT select Blue Bird or Green Thing.

        This is the exact bug scenario from the report.
        """
        spread = StorySpread(
            spread_number=1,
            text="He walked alone.",
            word_count=3,
            illustration_prompt="A robot walking through a forest",
            present_characters=None,  # Force fallback path
        )

        characters = illustrator._get_characters_for_spread(spread, clank_and_friends_outline)

        # Should NOT contain Blue Bird or Green Thing
        assert "The Blue Bird" not in characters
        assert "The Green Thing" not in characters
        # Should be empty (no character name appears as whole word)
        assert characters == []

    def test_the_does_not_match_the_blue_bird(self, illustrator, clank_and_friends_outline):
        """Token 'The' should not match 'The Blue Bird' as a partial match."""
        spread = StorySpread(
            spread_number=1,
            text="The forest was quiet.",
            word_count=4,
            illustration_prompt="A quiet forest scene",
            present_characters=None,
        )

        characters = illustrator._get_characters_for_spread(spread, clank_and_friends_outline)

        assert "The Blue Bird" not in characters
        assert "The Green Thing" not in characters

    def test_in_does_not_match_green_thing(self, illustrator, clank_and_friends_outline):
        """Token 'In' should not match any character."""
        spread = StorySpread(
            spread_number=1,
            text="In the morning, all was calm.",
            word_count=6,
            illustration_prompt="Morning scene",
            present_characters=None,
        )

        characters = illustrator._get_characters_for_spread(spread, clank_and_friends_outline)

        assert "The Green Thing" not in characters
        assert characters == []


# =============================================================================
# Test 2: Article-Stripped Matching
# =============================================================================

class TestArticleStrippedMatching:
    """Tests that article-stripped names match correctly."""

    def test_blue_bird_matches_the_blue_bird(self, illustrator, clank_and_friends_outline):
        """'blue bird' (no 'The') should match 'The Blue Bird'."""
        spread = StorySpread(
            spread_number=2,
            text="The blue bird flew overhead.",
            word_count=5,
            illustration_prompt="A blue bird in the sky",
            present_characters=None,
        )

        characters = illustrator._get_characters_for_spread(spread, clank_and_friends_outline)

        assert "The Blue Bird" in characters

    def test_green_thing_matches_the_green_thing(self, illustrator, clank_and_friends_outline):
        """'green thing' (no 'The') should match 'The Green Thing'."""
        spread = StorySpread(
            spread_number=3,
            text="A strange green thing appeared.",
            word_count=5,
            illustration_prompt="A mysterious green creature",
            present_characters=None,
        )

        characters = illustrator._get_characters_for_spread(spread, clank_and_friends_outline)

        assert "The Green Thing" in characters

    def test_full_name_with_article_matches(self, illustrator, clank_and_friends_outline):
        """'The Blue Bird' (full name) should match."""
        spread = StorySpread(
            spread_number=4,
            text="The Blue Bird sang a song.",
            word_count=6,
            illustration_prompt="Bird singing",
            present_characters=None,
        )

        characters = illustrator._get_characters_for_spread(spread, clank_and_friends_outline)

        assert "The Blue Bird" in characters


# =============================================================================
# Test 3: present_characters Override
# =============================================================================

class TestPresentCharactersOverride:
    """Tests that present_characters takes precedence over text heuristics."""

    def test_present_characters_overrides_text(self, illustrator, clank_and_friends_outline):
        """
        When present_characters is set, it should be used regardless of text content.
        """
        spread = StorySpread(
            spread_number=1,
            text="He walked alone in the forest.",  # Contains "He" and "The"
            word_count=6,
            illustration_prompt="Robot in forest",
            present_characters=["Clank"],  # Explicitly only Clank
        )

        characters = illustrator._get_characters_for_spread(spread, clank_and_friends_outline)

        assert characters == ["Clank"]
        assert "The Blue Bird" not in characters
        assert "The Green Thing" not in characters

    def test_present_characters_with_article_stripped_name(self, illustrator, clank_and_friends_outline):
        """present_characters=['Blue Bird'] should resolve to 'The Blue Bird'."""
        spread = StorySpread(
            spread_number=5,
            text="They met in the clearing.",
            word_count=5,
            illustration_prompt="Characters meeting",
            present_characters=["Blue Bird"],  # Without "The"
        )

        characters = illustrator._get_characters_for_spread(spread, clank_and_friends_outline)

        assert "The Blue Bird" in characters

    def test_present_characters_empty_list(self, illustrator, clank_and_friends_outline):
        """present_characters=[] should return empty list (no characters visible)."""
        spread = StorySpread(
            spread_number=6,
            text="The forest was empty. He had left.",
            word_count=7,
            illustration_prompt="Empty forest",
            present_characters=[],  # Explicitly no characters
        )

        characters = illustrator._get_characters_for_spread(spread, clank_and_friends_outline)

        assert characters == []


# =============================================================================
# Test 4: Helper Function Unit Tests
# =============================================================================

class TestNormalization:
    """Tests for normalization helper functions."""

    def test_normalize_name(self):
        """Test _normalize_name function."""
        assert _normalize_name("The Blue Bird") == "the blue bird"
        assert _normalize_name("  Clank  ") == "clank"
        assert _normalize_name("The   Green   Thing") == "the green thing"

    def test_strip_leading_article(self):
        """Test _strip_leading_article function."""
        assert _strip_leading_article("The Blue Bird") == "blue bird"
        assert _strip_leading_article("A Robot") == "robot"
        assert _strip_leading_article("An Elephant") == "elephant"
        assert _strip_leading_article("Clank") == "clank"  # No article


class TestNamesMatch:
    """Tests for _names_match function."""

    def test_exact_match(self):
        """Exact name matches."""
        assert _names_match("Clank", "Clank")
        assert _names_match("The Blue Bird", "The Blue Bird")

    def test_case_insensitive(self):
        """Case-insensitive matching."""
        assert _names_match("clank", "Clank")
        assert _names_match("THE BLUE BIRD", "The Blue Bird")

    def test_article_stripped_match(self):
        """Article-stripped matching."""
        assert _names_match("Blue Bird", "The Blue Bird")
        assert _names_match("Green Thing", "The Green Thing")
        assert _names_match("The Blue Bird", "Blue Bird")  # Both directions

    def test_no_substring_match(self):
        """Substring matching should NOT work."""
        assert not _names_match("Blue", "The Blue Bird")
        assert not _names_match("Bird", "The Blue Bird")
        assert not _names_match("He", "The Blue Bird")
        assert not _names_match("The", "The Blue Bird")


class TestStopwords:
    """Tests that stopwords are properly filtered."""

    def test_stopwords_include_common_words(self):
        """Verify critical stopwords are in the list."""
        critical_stopwords = ["he", "she", "the", "a", "an", "in", "on", "at", "to", "of"]
        for word in critical_stopwords:
            assert word in STOPWORDS, f"'{word}' should be in STOPWORDS"

    def test_extract_character_names_filters_stopwords(self, illustrator):
        """_extract_character_names should filter out stopwords."""
        text = "He walked to The forest. In a clearing, She saw Him."

        names = illustrator._extract_character_names(text)

        # None of these should appear
        assert "He" not in names
        assert "The" not in names
        assert "In" not in names
        assert "She" not in names
        assert "Him" not in names

    def test_extract_character_names_filters_short_tokens(self, illustrator):
        """_extract_character_names should filter tokens < 3 chars."""
        text = "Mr Fox and Dr Owl met in the park."

        names = illustrator._extract_character_names(text)

        # "Mr" and "Dr" are 2 chars, should be filtered
        # "Fox" and "Owl" are 3 chars, should be kept
        assert "Mr" not in names
        assert "Dr" not in names
        assert "Fox" in names
        assert "Owl" in names


# =============================================================================
# Test 5: Types Module Name Matching
# =============================================================================

class TestTypesModuleMatching:
    """Tests for get_character_bible and get_sheet methods."""

    def test_get_character_bible_exact_match(self, clank_and_friends_outline):
        """get_character_bible with exact name."""
        bible = clank_and_friends_outline.get_character_bible("Clank")
        assert bible is not None
        assert bible.name == "Clank"

    def test_get_character_bible_article_stripped(self, clank_and_friends_outline):
        """get_character_bible with article-stripped name."""
        bible = clank_and_friends_outline.get_character_bible("Blue Bird")
        assert bible is not None
        assert bible.name == "The Blue Bird"

    def test_get_character_bible_no_substring(self, clank_and_friends_outline):
        """get_character_bible should NOT do substring matching."""
        # "Blue" should not match "The Blue Bird"
        bible = clank_and_friends_outline.get_character_bible("Blue")
        assert bible is None

        # "He" should not match anything
        bible = clank_and_friends_outline.get_character_bible("He")
        assert bible is None

    def test_get_sheet_exact_match(self, sample_style):
        """get_sheet with exact name."""
        sheets = StoryReferenceSheets(story_title="Test")
        sheets.character_sheets["Clank"] = CharacterReferenceSheet(
            character_name="Clank",
            reference_image=b"fake",
            prompt_used="test",
        )

        sheet = sheets.get_sheet("Clank")
        assert sheet is not None
        assert sheet.character_name == "Clank"

    def test_get_sheet_article_stripped(self, sample_style):
        """get_sheet with article-stripped name."""
        sheets = StoryReferenceSheets(story_title="Test")
        sheets.character_sheets["The Blue Bird"] = CharacterReferenceSheet(
            character_name="The Blue Bird",
            reference_image=b"fake",
            prompt_used="test",
        )

        sheet = sheets.get_sheet("Blue Bird")
        assert sheet is not None
        assert sheet.character_name == "The Blue Bird"

    def test_get_sheet_no_substring(self, sample_style):
        """get_sheet should NOT do substring matching."""
        sheets = StoryReferenceSheets(story_title="Test")
        sheets.character_sheets["The Blue Bird"] = CharacterReferenceSheet(
            character_name="The Blue Bird",
            reference_image=b"fake",
            prompt_used="test",
        )

        # "He" should not match "The Blue Bird"
        sheet = sheets.get_sheet("He")
        assert sheet is None
