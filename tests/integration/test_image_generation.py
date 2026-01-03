"""
Integration tests for image generation with real API calls.

Run with: poetry run pytest tests/integration/test_image_generation.py -v
"""

import pytest
from PIL import Image
from io import BytesIO

from backend.config import get_image_client, get_image_model, get_image_config, extract_image_from_response
from backend.core.modules.character_sheet_generator import CharacterSheetGenerator
from backend.core.modules.spread_illustrator import SpreadIllustrator
from backend.core.types import (
    StorySpread,
    StoryMetadata,
    CharacterBible,
    StyleDefinition,
)


# =============================================================================
# Test extract_image_from_response with real API
# =============================================================================

@pytest.mark.requires_google_api
@pytest.mark.slow
class TestExtractImageFromResponseReal:
    """Tests that exercise extract_image_from_response with real API responses."""

    def test_extracts_image_from_real_response(self):
        """Verify extraction works with actual Gemini API response structure."""
        client = get_image_client()
        model = get_image_model()
        config = get_image_config()

        response = client.models.generate_content(
            model=model,
            contents="Generate a simple red circle on white background",
            config=config,
        )

        image_bytes = extract_image_from_response(response)

        # Verify we got valid image bytes
        assert isinstance(image_bytes, bytes)
        assert len(image_bytes) > 1000  # Real images are at least a few KB

        # Verify it's a valid image
        img = Image.open(BytesIO(image_bytes))
        assert img.size[0] > 0
        assert img.size[1] > 0


# =============================================================================
# Test CharacterSheetGenerator with real API
# =============================================================================

@pytest.mark.requires_google_api
@pytest.mark.slow
class TestCharacterSheetGeneratorReal:
    """Integration tests for character sheet generation."""

    @pytest.fixture
    def simple_character(self):
        """A simple character for testing."""
        return CharacterBible(
            name="Pip",
            species="small orange cat",
            age_appearance="young kitten",
            body="fluffy and round",
            face="big eyes, pink nose",
            hair="orange tabby fur",
            eyes="large green eyes",
            clothing="blue collar with bell",
            signature_item="tiny bell on collar",
            color_palette=["orange", "white", "blue"],
            style_tags=["cute", "cartoon"],
        )

    @pytest.fixture
    def simple_style(self):
        """A simple illustration style for testing."""
        return StyleDefinition(
            name="Simple Cartoon",
            description="Clean cartoon style for testing",
            prompt_prefix="Children's book illustration in simple cartoon style with clean lines",
            best_for=["animals"],
            lighting_direction="soft even studio lighting",
        )

    def test_generates_character_reference(self, simple_character, simple_style):
        """Generates a valid character reference sheet."""
        generator = CharacterSheetGenerator()

        result = generator.generate_reference(simple_character, simple_style)

        # Verify result structure
        assert result.character_name == "Pip"
        assert isinstance(result.reference_image, bytes)
        assert len(result.reference_image) > 5000  # Real image

        # Verify it's a valid image
        img = result.to_pil_image()
        assert img.size[0] > 100
        assert img.size[1] > 100


# =============================================================================
# Test SpreadIllustrator with real API
# =============================================================================

@pytest.mark.requires_google_api
@pytest.mark.slow
class TestSpreadIllustratorReal:
    """Integration tests for spread illustration."""

    @pytest.fixture
    def simple_spread(self):
        """A simple spread for testing."""
        return StorySpread(
            spread_number=1,
            text="The little cat sat on the sunny windowsill.",
            word_count=8,
            was_revised=False,
            illustration_prompt="A small orange cat sitting on a windowsill with sunlight streaming in.",
        )

    @pytest.fixture
    def simple_outline(self):
        """Minimal metadata for testing."""
        return StoryMetadata(
            title="The Sunny Cat",
            setting="A cozy house",
            character_bibles=[],
            illustration_style=StyleDefinition(
                name="Simple Cartoon",
                description="Clean cartoon style",
                prompt_prefix="Children's book illustration in simple cartoon style with clean lines and warm colors",
                best_for=["animals"],
                lighting_direction="soft even studio lighting",
            ),
            style_rationale="Simple style for simple story",
        )

    def test_illustrates_single_spread(self, simple_spread, simple_outline):
        """Generates illustration for a single spread."""
        illustrator = SpreadIllustrator()

        image_bytes = illustrator.illustrate_spread(simple_spread, simple_outline)

        # Verify we got a valid image
        assert isinstance(image_bytes, bytes)
        assert len(image_bytes) > 5000

        img = Image.open(BytesIO(image_bytes))
        assert img.size[0] > 100
        assert img.size[1] > 100

    def test_illustrates_multiple_spreads(self, simple_outline):
        """Generates illustrations for multiple spreads."""
        spreads = [
            StorySpread(
                spread_number=i,
                text=f"Spread {i} text",
                word_count=3,
                was_revised=False,
                illustration_prompt=f"Scene {i}: A cat doing something cute.",
            )
            for i in range(1, 3)  # Just 2 spreads to save API costs
        ]

        illustrator = SpreadIllustrator()

        result = illustrator.illustrate_story(spreads, simple_outline)

        assert len(result) == 2
        assert all(s.illustration_image is not None for s in result)
        assert all(len(s.illustration_image) > 5000 for s in result)
