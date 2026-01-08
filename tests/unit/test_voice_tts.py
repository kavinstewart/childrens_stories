"""Unit tests for voice TTS WebSocket endpoint."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.auth.tokens import create_access_token


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def create_mock_cartesia_ws():
    """Create a mock Cartesia WebSocket."""

    class MockCartesiaWS:
        def __init__(self):
            self.sent_messages = []
            self.closed = False

        async def send(self, **kwargs):
            self.sent_messages.append(kwargs)
            # Return async generator with audio chunks
            async def generate():
                yield {"type": "chunk", "data": b"test audio data"}
                yield {"type": "done"}
            return generate()

        async def close(self):
            self.closed = True

    return MockCartesiaWS()


def create_mock_cartesia_client(mock_ws):
    """Create a mock Cartesia client."""

    class MockTTS:
        async def websocket(self):
            return mock_ws

    class MockCartesiaClient:
        def __init__(self, api_key):
            self.tts = MockTTS()

        async def close(self):
            pass

    return MockCartesiaClient


class TestTTSWebSocket:
    """Tests for the /voice/tts WebSocket endpoint."""

    def test_tts_rejects_unauthenticated(self):
        """Test that TTS rejects unauthenticated connections."""
        client = TestClient(app)
        with client.websocket_connect("/voice/tts") as websocket:
            # Should receive auth error
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "authentication" in data["message"].lower()

    def test_tts_rejects_without_cartesia_key(self):
        """Test that TTS returns error when CARTESIA_API_KEY is not set."""
        token = create_access_token(subject="test_user")
        with patch("backend.api.routes.voice.tts.CARTESIA_API_KEY", ""):
            client = TestClient(app)
            with client.websocket_connect("/voice/tts") as websocket:
                # Send auth
                websocket.send_json({"type": "auth", "token": token})
                # Should receive error message
                data = websocket.receive_json()
                assert data["type"] == "error"
                assert "not configured" in data["message"].lower()

    def test_tts_connects_with_cartesia_key(self):
        """Test that TTS connects successfully when CARTESIA_API_KEY is set."""
        token = create_access_token(subject="test_user")
        mock_ws = create_mock_cartesia_ws()

        with patch("backend.api.routes.voice.tts.CARTESIA_API_KEY", "test-key"):
            with patch("backend.api.routes.voice.tts.AsyncCartesia", create_mock_cartesia_client(mock_ws)):
                client = TestClient(app)
                with client.websocket_connect("/voice/tts") as websocket:
                    # Send auth
                    websocket.send_json({"type": "auth", "token": token})
                    # Should receive connected message
                    data = websocket.receive_json()
                    assert data["type"] == "connected"
                    assert data["message"] == "TTS ready"

    def test_tts_rejects_empty_text(self):
        """Test that TTS rejects synthesize requests with empty text."""
        token = create_access_token(subject="test_user")
        mock_ws = create_mock_cartesia_ws()

        with patch("backend.api.routes.voice.tts.CARTESIA_API_KEY", "test-key"):
            with patch("backend.api.routes.voice.tts.AsyncCartesia", create_mock_cartesia_client(mock_ws)):
                client = TestClient(app)
                with client.websocket_connect("/voice/tts") as websocket:
                    # Send auth
                    websocket.send_json({"type": "auth", "token": token})
                    data = websocket.receive_json()
                    assert data["type"] == "connected"

                    # Send empty text
                    websocket.send_json({"type": "synthesize", "text": ""})
                    data = websocket.receive_json()
                    assert data["type"] == "error"
                    assert "no text" in data["message"].lower()

    def test_tts_rejects_long_text(self):
        """Test that TTS rejects text that's too long."""
        token = create_access_token(subject="test_user")
        mock_ws = create_mock_cartesia_ws()

        with patch("backend.api.routes.voice.tts.CARTESIA_API_KEY", "test-key"):
            with patch("backend.api.routes.voice.tts.AsyncCartesia", create_mock_cartesia_client(mock_ws)):
                client = TestClient(app)
                with client.websocket_connect("/voice/tts") as websocket:
                    # Send auth
                    websocket.send_json({"type": "auth", "token": token})
                    data = websocket.receive_json()
                    assert data["type"] == "connected"

                    # Send very long text
                    websocket.send_json({"type": "synthesize", "text": "x" * 10000})
                    data = websocket.receive_json()
                    assert data["type"] == "error"
                    assert "too long" in data["message"].lower()

    def test_tts_handles_stop(self):
        """Test that TTS handles stop message gracefully."""
        token = create_access_token(subject="test_user")
        mock_ws = create_mock_cartesia_ws()

        with patch("backend.api.routes.voice.tts.CARTESIA_API_KEY", "test-key"):
            with patch("backend.api.routes.voice.tts.AsyncCartesia", create_mock_cartesia_client(mock_ws)):
                client = TestClient(app)
                with client.websocket_connect("/voice/tts") as websocket:
                    # Send auth
                    websocket.send_json({"type": "auth", "token": token})
                    data = websocket.receive_json()
                    assert data["type"] == "connected"

                    # Send stop
                    websocket.send_json({"type": "stop"})
                    # Connection should close without error


class TestTTSConfiguration:
    """Tests for TTS configuration."""

    def test_max_text_length_is_reasonable(self):
        """Test that max text length is set to a reasonable value."""
        from backend.api.routes.voice.tts import MAX_TEXT_LENGTH
        assert MAX_TEXT_LENGTH >= 1000
        assert MAX_TEXT_LENGTH <= 10000

    def test_default_voice_id_is_set(self):
        """Test that a default voice ID is configured."""
        from backend.api.routes.voice.tts import DEFAULT_VOICE_ID
        assert DEFAULT_VOICE_ID  # Not empty
        assert len(DEFAULT_VOICE_ID) > 10  # Looks like a UUID


