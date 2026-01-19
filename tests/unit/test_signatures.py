"""Unit tests for DSPy signatures."""

import pytest
import dspy

from backend.core.signatures import (
    DirectStorySignature,
    IllustrationStyleSignature,
    CharacterExtractorSignature,
    EntityBibleSignature,
)


def get_field_desc(signature_class, field_name: str) -> str:
    """Extract the desc from a DSPy signature field."""
    field_info = signature_class.model_fields[field_name]
    extra = field_info.json_schema_extra or {}
    return extra.get("desc", "")


class TestDirectStorySignature:
    """Tests for DirectStorySignature."""

    def test_has_required_input_fields(self):
        """Should have goal and reference_examples as inputs."""
        fields = DirectStorySignature.model_fields
        assert "goal" in fields
        assert "reference_examples" in fields

    def test_has_story_output_field(self):
        """Should have story as output."""
        fields = DirectStorySignature.model_fields
        assert "story" in fields

    def test_docstring_contains_structure_guidance(self):
        """Should have comprehensive guidance in docstring."""
        docstring = DirectStorySignature.__doc__
        assert "12 spreads" in docstring
        assert "400-600 words" in docstring
        assert "PACING" in docstring
        assert "OUTPUT FORMAT" in docstring

    def test_output_field_is_concise(self):
        """Output field desc should not duplicate the full docstring format."""
        desc = get_field_desc(DirectStorySignature, "story")
        # Should reference format but not duplicate the full specification
        # Currently the desc is ~500 chars with full duplication - should be < 200
        assert len(desc) < 200, f"Output field desc is too long ({len(desc)} chars), likely duplicates docstring"


class TestIllustrationStyleSignature:
    """Tests for IllustrationStyleSignature."""

    def test_has_required_fields(self):
        """Should have story_summary input and selected_style output."""
        fields = IllustrationStyleSignature.model_fields
        assert "story_summary" in fields
        assert "selected_style" in fields

    def test_docstring_contains_style_guidance(self):
        """Should have guidance about style selection."""
        docstring = IllustrationStyleSignature.__doc__
        assert docstring is not None
        # Should have meaningful guidance, not just one line
        assert len(docstring) > 100, f"Docstring is too short ({len(docstring)} chars): '{docstring}'"


class TestCharacterExtractorSignature:
    """Tests for CharacterExtractorSignature."""

    def test_has_required_fields(self):
        """Should have story_text input and characters output."""
        fields = CharacterExtractorSignature.model_fields
        assert "story_text" in fields
        assert "characters" in fields

    def test_docstring_has_format_guidance(self):
        """Should explain the NAME: | DETAILS: format."""
        docstring = CharacterExtractorSignature.__doc__
        assert "NAME:" in docstring
        assert "DETAILS:" in docstring


class TestEntityBibleSignature:
    """Tests for EntityBibleSignature."""

    def test_has_required_fields(self):
        """Should have extracted_entities input and entity_bibles output."""
        fields = EntityBibleSignature.model_fields
        assert "extracted_entities" in fields
        assert "entity_bibles" in fields

    def test_docstring_has_visual_format(self):
        """Should explain the visual bible format."""
        docstring = EntityBibleSignature.__doc__
        assert "CHARACTER:" in docstring
        assert "SPECIES:" in docstring
        assert "COLOR_PALETTE:" in docstring
