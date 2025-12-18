"""Unit tests for SpreadIllustrator with mocked API client."""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

from backend.core.modules.spread_illustrator import SpreadIllustrator
from backend.core.types import (
    StorySpread,
    StoryOutline,
    StoryReferenceSheets,
    CharacterReferenceSheet,
    CharacterBible,
    StyleDefinition,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_spread():
    """A story spread with illustration prompt."""
    return StorySpread(
        spread_number=1,
        text="Luna looked up at the stars and smiled.",
        word_count=8,
        was_revised=False,
        illustration_prompt="A young girl looking up at a starry night sky, filled with wonder.",
    )


@pytest.fixture
def sample_character_bible():
    """A character bible for testing."""
    return CharacterBible(
        name="Luna",
        species="human girl",
        age_appearance="7 years old",
        body="small and slender",
        face="round with freckles",
        hair="long curly red hair",
        eyes="big green eyes",
        clothing="blue dress with stars",
        signature_item="telescope necklace",
        color_palette=["blue", "silver", "red"],
        style_tags=["whimsical", "warm"],
    )


@pytest.fixture
def sample_style():
    """An illustration style for testing."""
    return StyleDefinition(
        name="Watercolor",
        description="Soft watercolor style",
        prompt_prefix="Watercolor children's book illustration.",
        prompt_suffix="Soft edges, warm colors.",
        best_for=["nature", "emotions"],
    )


@pytest.fixture
def sample_outline(sample_character_bible, sample_style):
    """A story outline with character bibles."""
    return StoryOutline(
        title="Luna and the Stars",
        protagonist_goal="Learn about constellations",
        stakes="Missing the meteor shower",
        characters="Luna - a curious 7-year-old girl",
        setting="A backyard on a summer night",
        emotional_arc="Wonder -> frustration -> discovery -> joy",
        plot_summary="Luna learns to find constellations",
        spread_breakdown="Spread 1: Luna looks at the sky",
        moral="Patience reveals hidden wonders",
        goal="Teach about stars",
        character_bibles=[sample_character_bible],
        illustration_style=sample_style,
        style_rationale="Watercolor suits the dreamy night theme",
    )


@pytest.fixture
def sample_reference_sheet():
    """A character reference sheet with fake image bytes."""
    return CharacterReferenceSheet(
        character_name="Luna",
        reference_image=b"fake png bytes for Luna",
        prompt_used="Character sheet for Luna",
        character_description="7 years old, human girl, round with freckles",
    )


@pytest.fixture
def sample_reference_sheets(sample_reference_sheet):
    """Reference sheets collection."""
    sheets = StoryReferenceSheets(story_title="Luna and the Stars")
    sheets.character_sheets["Luna"] = sample_reference_sheet
    return sheets


@pytest.fixture
def mock_image_client():
    """Mock Google genai client that returns fake image."""
    client = MagicMock()

    # Create fake response structure
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
# Tests for _extract_character_names
# =============================================================================

class TestExtractCharacterNames:
    """Tests for character name extraction from text."""

    def test_extracts_capitalized_names(self, illustrator):
        """Finds capitalized words that could be names."""
        text = "Luna looked at Max and smiled."

        names = illustrator._extract_character_names(text)

        assert "Luna" in names
        assert "Max" in names

    def test_deduplicates_names(self, illustrator):
        """Returns unique names even if mentioned multiple times."""
        text = "Luna said hello. Luna waved goodbye."

        names = illustrator._extract_character_names(text)

        assert names.count("Luna") == 1

    def test_ignores_lowercase_words(self, illustrator):
        """Doesn't extract regular lowercase words."""
        text = "the girl looked at the stars"

        names = illustrator._extract_character_names(text)

        assert "the" not in names
        assert "girl" not in names

    def test_handles_empty_text(self, illustrator):
        """Returns empty list for empty text."""
        names = illustrator._extract_character_names("")

        assert names == []


# =============================================================================
# Tests for _build_contents
# =============================================================================

class TestBuildContents:
    """Tests for multimodal content list construction."""

    def test_includes_scene_prompt(self, illustrator, sample_spread, sample_outline):
        """Scene prompt is always included in contents."""
        scene_prompt = "Generate an illustration..."

        contents = illustrator._build_contents(
            sample_spread, sample_outline, None, scene_prompt
        )

        assert scene_prompt in contents

    def test_adds_character_references_when_provided(
        self, illustrator, sample_spread, sample_outline, sample_reference_sheets
    ):
        """Includes character reference images when available."""
        scene_prompt = "Generate an illustration..."

        # Mock to_pil_image to return a fake image
        with patch.object(
            sample_reference_sheets.character_sheets["Luna"],
            'to_pil_image',
            return_value=MagicMock()
        ):
            contents = illustrator._build_contents(
                sample_spread, sample_outline, sample_reference_sheets, scene_prompt
            )

        # Should have: [image, description, prompt]
        assert len(contents) >= 2
        # Description should mention the character
        assert any("Luna" in str(c) for c in contents)

    def test_works_without_reference_sheets(
        self, illustrator, sample_spread, sample_outline
    ):
        """Works correctly when no reference sheets provided."""
        scene_prompt = "Generate an illustration..."

        contents = illustrator._build_contents(
            sample_spread, sample_outline, None, scene_prompt
        )

        # Should just have the prompt
        assert contents == [scene_prompt]

    def test_respects_max_references_limit(
        self, illustrator, sample_spread, sample_outline, sample_reference_sheets
    ):
        """Doesn't exceed max_reference_images limit."""
        # Add many characters
        for i in range(20):
            bible = CharacterBible(
                name=f"Character{i}",
                species="test",
                age_appearance="test",
                body="test",
                face="test",
                hair="test",
                eyes="test",
                clothing="test",
                signature_item="test",
                color_palette=[],
                style_tags=[],
            )
            sample_outline.character_bibles.append(bible)
            sample_reference_sheets.character_sheets[f"Character{i}"] = CharacterReferenceSheet(
                character_name=f"Character{i}",
                reference_image=b"fake",
                prompt_used="test",
                character_description="test",
            )

        scene_prompt = "Generate an illustration..."

        with patch.object(
            CharacterReferenceSheet,
            'to_pil_image',
            return_value=MagicMock()
        ):
            contents = illustrator._build_contents(
                sample_spread, sample_outline, sample_reference_sheets, scene_prompt
            )

        # Count non-string items (images)
        image_count = sum(1 for c in contents if not isinstance(c, str))

        # Should not exceed limit (14)
        assert image_count <= 14


# =============================================================================
# Tests for illustrate_spread
# =============================================================================

class TestIllustrateSpread:
    """Tests for single spread illustration."""

    def test_returns_image_bytes(
        self, illustrator, mock_image_client, sample_spread, sample_outline
    ):
        """Returns image bytes from API response."""
        result = illustrator.illustrate_spread(sample_spread, sample_outline)

        assert result == b"generated image bytes"

    def test_calls_api_with_correct_model(
        self, illustrator, mock_image_client, sample_spread, sample_outline
    ):
        """Uses configured model for API call."""
        illustrator.illustrate_spread(sample_spread, sample_outline)

        mock_image_client.models.generate_content.assert_called_once()
        call_kwargs = mock_image_client.models.generate_content.call_args
        assert call_kwargs.kwargs['model'] == 'test-model'

    def test_raises_with_spread_number_on_failure(
        self, illustrator, mock_image_client, sample_spread, sample_outline
    ):
        """Error message includes spread number for debugging."""
        # Make API return no image
        mock_image_client.models.generate_content.return_value.candidates[0].content.parts = []

        with pytest.raises(ValueError, match="spread 1"):
            illustrator.illustrate_spread(sample_spread, sample_outline)


# =============================================================================
# Tests for illustrate_story
# =============================================================================

class TestIllustrateStory:
    """Tests for multi-spread illustration."""

    def test_illustrates_all_spreads(
        self, illustrator, mock_image_client, sample_outline
    ):
        """Generates illustration for each spread."""
        spreads = [
            StorySpread(spread_number=1, text="Spread 1", word_count=2, was_revised=False, illustration_prompt="Scene 1"),
            StorySpread(spread_number=2, text="Spread 2", word_count=2, was_revised=False, illustration_prompt="Scene 2"),
            StorySpread(spread_number=3, text="Spread 3", word_count=2, was_revised=False, illustration_prompt="Scene 3"),
        ]

        result = illustrator.illustrate_story(spreads, sample_outline)

        assert len(result) == 3
        assert all(s.illustration_image == b"generated image bytes" for s in result)

    def test_continues_on_failure(
        self, illustrator, mock_image_client, sample_outline
    ):
        """Continues illustrating other spreads if one fails."""
        spreads = [
            StorySpread(spread_number=1, text="Spread 1", word_count=2, was_revised=False, illustration_prompt="Scene 1"),
            StorySpread(spread_number=2, text="Spread 2", word_count=2, was_revised=False, illustration_prompt="Scene 2"),
        ]

        # Fail on first call, succeed on second
        fake_part = MagicMock()
        fake_part.inline_data = MagicMock()
        fake_part.inline_data.data = b"image bytes"

        mock_image_client.models.generate_content.side_effect = [
            Exception("API error"),
            MagicMock(candidates=[MagicMock(content=MagicMock(parts=[fake_part]))]),
        ]

        result = illustrator.illustrate_story(spreads, sample_outline)

        assert result[0].illustration_image is None  # Failed
        assert result[1].illustration_image == b"image bytes"  # Succeeded
