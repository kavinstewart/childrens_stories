"""Unit tests for TTS timestamp transformation."""
import pytest


class MockWordTimestamps:
    """Mock Cartesia WordTimestamps object."""
    def __init__(self, words: list, start: list, end: list):
        self.words = words
        self.start = start
        self.end = end


def transform_timestamps(word_timestamps) -> list:
    """Transform Cartesia timestamps to frontend format.
    
    Cartesia sends: words=["Hello","world"], start=[0.0,0.5], end=[0.3,0.8]
    We need: [{word:"Hello",start:0.0,end:0.3}, ...]
    """
    words_list = getattr(word_timestamps, "words", [])
    start_list = getattr(word_timestamps, "start", [])
    end_list = getattr(word_timestamps, "end", [])

    combined = []
    for i, word in enumerate(words_list):
        combined.append({
            "word": word,
            "start": start_list[i] if i < len(start_list) else 0,
            "end": end_list[i] if i < len(end_list) else 0,
        })
    return combined


class TestTimestampTransformation:
    """Tests for timestamp transformation logic."""

    def test_transforms_cartesia_format_to_frontend_format(self):
        """Cartesia parallel arrays should become array of objects."""
        cartesia_ts = MockWordTimestamps(
            words=["Hello", "world"],
            start=[0.0, 0.5],
            end=[0.3, 0.8]
        )
        
        result = transform_timestamps(cartesia_ts)
        
        assert len(result) == 2
        assert result[0] == {"word": "Hello", "start": 0.0, "end": 0.3}
        assert result[1] == {"word": "world", "start": 0.5, "end": 0.8}

    def test_handles_single_word(self):
        """Single word timestamps should work."""
        cartesia_ts = MockWordTimestamps(
            words=["Hi"],
            start=[0.0],
            end=[0.2]
        )
        
        result = transform_timestamps(cartesia_ts)
        
        assert len(result) == 1
        assert result[0] == {"word": "Hi", "start": 0.0, "end": 0.2}

    def test_handles_empty_timestamps(self):
        """Empty timestamps should return empty list."""
        cartesia_ts = MockWordTimestamps(
            words=[],
            start=[],
            end=[]
        )
        
        result = transform_timestamps(cartesia_ts)
        
        assert result == []

    def test_handles_mismatched_arrays_gracefully(self):
        """If arrays are mismatched, should default missing values to 0."""
        cartesia_ts = MockWordTimestamps(
            words=["Hello", "world", "test"],
            start=[0.0, 0.5],  # Missing third
            end=[0.3]  # Missing second and third
        )
        
        result = transform_timestamps(cartesia_ts)
        
        assert len(result) == 3
        assert result[0] == {"word": "Hello", "start": 0.0, "end": 0.3}
        assert result[1] == {"word": "world", "start": 0.5, "end": 0}
        assert result[2] == {"word": "test", "start": 0, "end": 0}
