"""Unit tests for backend/core/types.py functions."""

import pytest

from backend.core.types import (
    build_illustration_prompt,
    DEFAULT_STYLE_PREFIX,
    DEFAULT_LIGHTING,
)


# =============================================================================
# build_illustration_prompt tests
# =============================================================================


class TestBuildIllustrationPrompt:
    """Tests for the build_illustration_prompt function."""

    def test_builds_prompt_with_all_fields(self):
        """Should compose all fields into the expected format."""
        result = build_illustration_prompt(
            illustration_prompt="A fox dancing in a meadow",
            style_prefix="Warm watercolor style",
            lighting="golden hour sunlight",
        )

        assert "Warm watercolor style, 16:9 aspect ratio in landscape format." in result
        assert "Scene: A fox dancing in a meadow" in result
        assert "Lighting: golden hour sunlight." in result
        assert "Wide shot framing with space at bottom for text overlay" in result
        assert "Maintain exact character identity from reference images above" in result

    def test_uses_default_style_prefix(self):
        """Should work with default style prefix constant."""
        result = build_illustration_prompt(
            illustration_prompt="Test scene",
            style_prefix=DEFAULT_STYLE_PREFIX,
            lighting=DEFAULT_LIGHTING,
        )

        assert DEFAULT_STYLE_PREFIX in result
        assert DEFAULT_LIGHTING in result

    def test_preserves_empty_illustration_prompt(self):
        """Should handle empty illustration prompt gracefully."""
        result = build_illustration_prompt(
            illustration_prompt="",
            style_prefix="Digital cartoon style",
            lighting="soft ambient light",
        )

        assert "Scene: " in result
        assert "Lighting: soft ambient light." in result

    def test_multiline_format(self):
        """Should produce multiline output with proper structure."""
        result = build_illustration_prompt(
            illustration_prompt="Test",
            style_prefix="Style",
            lighting="Light",
        )

        lines = result.strip().split("\n")
        # Should have multiple lines (style, blank, scene, blank, lighting, blank, framing)
        assert len(lines) >= 5

    def test_aspect_ratio_in_landscape_format(self):
        """Should include the correct aspect ratio language."""
        result = build_illustration_prompt(
            illustration_prompt="Any scene",
            style_prefix="Any style",
            lighting="Any lighting",
        )

        assert "16:9 aspect ratio in landscape format" in result
        # Ensure old language is not present
        assert "double-page spread composition" not in result
