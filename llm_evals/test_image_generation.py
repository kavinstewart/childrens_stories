"""
Integration tests for image generation with real API calls.

Run with: poetry run pytest llm_evals/test_image_generation.py -v
"""

import pytest
from PIL import Image
from io import BytesIO

from src.config import get_image_client, get_image_model, get_image_config, extract_image_from_response
from src.modules.character_sheet_generator import CharacterSheetGenerator
from src.modules.page_illustrator import PageIllustrator
from src.types import (
    StoryPage,
    StoryOutline,
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

    def test_generates_character_reference(self, simple_character):
        """Generates a valid character reference sheet."""
        generator = CharacterSheetGenerator()

        result = generator.generate_reference(simple_character)

        # Verify result structure
        assert result.character_name == "Pip"
        assert isinstance(result.reference_image, bytes)
        assert len(result.reference_image) > 5000  # Real image

        # Verify it's a valid image
        img = result.to_pil_image()
        assert img.size[0] > 100
        assert img.size[1] > 100


# =============================================================================
# Test PageIllustrator with real API
# =============================================================================

@pytest.mark.requires_google_api
@pytest.mark.slow
class TestPageIllustratorReal:
    """Integration tests for page illustration."""

    @pytest.fixture
    def simple_page(self):
        """A simple page for testing."""
        return StoryPage(
            page_number=1,
            text="The little cat sat on the sunny windowsill.",
            word_count=8,
            was_revised=False,
            illustration_prompt="A small orange cat sitting on a windowsill with sunlight streaming in.",
        )

    @pytest.fixture
    def simple_outline(self):
        """A minimal outline for testing."""
        return StoryOutline(
            title="The Sunny Cat",
            protagonist_goal="Find a warm spot",
            stakes="Being cold",
            characters="Pip - an orange kitten",
            setting="A cozy house",
            emotional_arc="Content",
            plot_summary="A cat finds a sunny spot",
            page_breakdown="Page 1: Cat sits in sun",
            moral="Simple pleasures are best",
            goal="Relaxation",
            character_bibles=[],
            illustration_style=StyleDefinition(
                name="Simple Cartoon",
                description="Clean cartoon style",
                prompt_prefix="Children's book illustration, simple cartoon style.",
                prompt_suffix="Clean lines, warm colors, appealing to children.",
                best_for=["animals"],
            ),
            style_rationale="Simple style for simple story",
        )

    def test_illustrates_single_page(self, simple_page, simple_outline):
        """Generates illustration for a single page."""
        illustrator = PageIllustrator()

        image_bytes = illustrator.illustrate_page(simple_page, simple_outline)

        # Verify we got a valid image
        assert isinstance(image_bytes, bytes)
        assert len(image_bytes) > 5000

        img = Image.open(BytesIO(image_bytes))
        assert img.size[0] > 100
        assert img.size[1] > 100

    def test_illustrates_multiple_pages(self, simple_outline):
        """Generates illustrations for multiple pages."""
        pages = [
            StoryPage(
                page_number=i,
                text=f"Page {i} text",
                word_count=3,
                was_revised=False,
                illustration_prompt=f"Scene {i}: A cat doing something cute.",
            )
            for i in range(1, 3)  # Just 2 pages to save API costs
        ]

        illustrator = PageIllustrator()

        result = illustrator.illustrate_story(pages, simple_outline)

        assert len(result) == 2
        assert all(p.illustration_image is not None for p in result)
        assert all(len(p.illustration_image) > 5000 for p in result)
