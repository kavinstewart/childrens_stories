"""Unit tests for image extraction from Gemini API responses."""

import pytest
from unittest.mock import MagicMock
import base64

from src.config.image import extract_image_from_response


class FakePart:
    """Fake Gemini response part."""
    def __init__(self, image_data=None):
        if image_data is not None:
            self.inline_data = MagicMock()
            self.inline_data.data = image_data
        else:
            self.inline_data = None


class FakeCandidate:
    """Fake Gemini response candidate."""
    def __init__(self, parts):
        self.content = MagicMock()
        self.content.parts = parts


class FakeResponse:
    """Fake Gemini API response."""
    def __init__(self, parts):
        self.candidates = [FakeCandidate(parts)]


class TestExtractImageFromResponse:
    """Tests for extract_image_from_response()."""

    def test_extracts_raw_bytes(self):
        """Returns bytes directly when response contains raw bytes."""
        image_bytes = b"\x89PNG\r\n\x1a\n fake image data"
        response = FakeResponse([FakePart(image_bytes)])

        result = extract_image_from_response(response)

        assert result == image_bytes

    def test_decodes_base64_string(self):
        """Decodes base64 string when response contains encoded data."""
        original_bytes = b"\x89PNG\r\n\x1a\n fake image data"
        encoded = base64.b64encode(original_bytes).decode('utf-8')
        response = FakeResponse([FakePart(encoded)])

        result = extract_image_from_response(response)

        assert result == original_bytes

    def test_raises_when_no_image_in_response(self):
        """Raises ValueError when response has no image parts."""
        response = FakeResponse([FakePart(None)])  # Part without inline_data

        with pytest.raises(ValueError, match="No image found"):
            extract_image_from_response(response)

    def test_raises_when_parts_list_empty(self):
        """Raises ValueError when response has empty parts list."""
        response = FakeResponse([])

        with pytest.raises(ValueError, match="No image found"):
            extract_image_from_response(response)

    def test_extracts_first_image_when_multiple_parts(self):
        """Returns first image when response contains multiple parts."""
        first_image = b"first image"
        second_image = b"second image"
        response = FakeResponse([
            FakePart(first_image),
            FakePart(second_image),
        ])

        result = extract_image_from_response(response)

        assert result == first_image

    def test_skips_non_image_parts(self):
        """Skips parts without inline_data to find the image."""
        image_bytes = b"the actual image"
        response = FakeResponse([
            FakePart(None),  # Text part (no inline_data)
            FakePart(image_bytes),  # Image part
        ])

        result = extract_image_from_response(response)

        assert result == image_bytes
