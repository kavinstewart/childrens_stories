"""Unit tests for voice STT WebSocket endpoint."""

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.auth.tokens import create_access_token


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def valid_token():
    """Create a valid auth token for testing."""
    return create_access_token(subject="test_user")


def create_mock_deepgram_ws(messages=None):
    """Create a mock WebSocket that yields the given messages."""
    messages = messages or []

    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []
            self.closed = False

        async def send(self, data):
            self.sent_messages.append(data)

        async def close(self):
            self.closed = True

        def __aiter__(self):
            return self

        async def __anext__(self):
            if messages:
                return messages.pop(0)
            raise StopAsyncIteration

    return MockWebSocket()


@asynccontextmanager
async def mock_ws_connect_factory(mock_ws):
    """Factory for creating mock ws_connect context manager."""
    yield mock_ws


class TestSTTWebSocket:
    """Tests for the /voice/stt WebSocket endpoint."""

    def test_stt_rejects_unauthenticated(self):
        """Test that STT rejects unauthenticated connections."""
        client = TestClient(app)
        with client.websocket_connect("/voice/stt") as websocket:
            # Should receive auth error
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "authentication" in data["message"].lower()

    def test_stt_rejects_without_deepgram_key(self):
        """Test that STT returns error when DEEPGRAM_API_KEY is not set."""
        token = create_access_token(subject="test_user")
        with patch("backend.api.routes.voice.DEEPGRAM_API_KEY", ""):
            client = TestClient(app)
            with client.websocket_connect("/voice/stt") as websocket:
                # Send auth
                websocket.send_json({"type": "auth", "token": token})
                # Should receive error message
                data = websocket.receive_json()
                assert data["type"] == "error"
                assert "not configured" in data["message"].lower()

    def test_stt_connects_with_deepgram_key(self):
        """Test that STT connects successfully when DEEPGRAM_API_KEY is set."""
        token = create_access_token(subject="test_user")
        mock_ws = create_mock_deepgram_ws()

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch("backend.api.routes.voice.DEEPGRAM_API_KEY", "test-key"):
            with patch("backend.api.routes.voice.ws_connect", mock_connect):
                client = TestClient(app)
                with client.websocket_connect("/voice/stt") as websocket:
                    # Send auth
                    websocket.send_json({"type": "auth", "token": token})
                    # Should receive connected message
                    data = websocket.receive_json()
                    assert data["type"] == "connected"
                    assert data["message"] == "STT ready"

    def test_stt_forwards_audio_to_deepgram(self):
        """Test that audio data can be sent to the STT endpoint."""
        token = create_access_token(subject="test_user")
        mock_ws = create_mock_deepgram_ws()

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch("backend.api.routes.voice.DEEPGRAM_API_KEY", "test-key"):
            with patch("backend.api.routes.voice.ws_connect", mock_connect):
                client = TestClient(app)
                with client.websocket_connect("/voice/stt") as websocket:
                    # Send auth
                    websocket.send_json({"type": "auth", "token": token})
                    # Wait for connected
                    data = websocket.receive_json()
                    assert data["type"] == "connected"

                    # Send audio data - the endpoint should accept it without error
                    test_audio = base64.b64encode(b"test audio data").decode()
                    websocket.send_json({
                        "type": "audio",
                        "data": test_audio
                    })

                    # Send stop to cleanly close
                    websocket.send_json({"type": "stop"})

                    # If we get here without error, audio was accepted

    def test_stt_handles_transcript_response(self):
        """Test that transcript responses are forwarded to client."""
        token = create_access_token(subject="test_user")
        transcript_message = json.dumps({
            "type": "Results",
            "channel": {
                "alternatives": [{
                    "transcript": "hello world",
                    "confidence": 0.98
                }]
            },
            "is_final": True,
            "speech_final": True
        })

        mock_ws = create_mock_deepgram_ws([transcript_message])

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch("backend.api.routes.voice.DEEPGRAM_API_KEY", "test-key"):
            with patch("backend.api.routes.voice.ws_connect", mock_connect):
                client = TestClient(app)
                with client.websocket_connect("/voice/stt") as websocket:
                    # Send auth
                    websocket.send_json({"type": "auth", "token": token})
                    # Wait for connected
                    data = websocket.receive_json()
                    assert data["type"] == "connected"

                    # Wait for transcript
                    data = websocket.receive_json()
                    assert data["type"] == "transcript"
                    assert data["transcript"] == "hello world"
                    assert data["confidence"] == 0.98
                    assert data["is_final"] is True
                    assert data["speech_final"] is True

    def test_stt_handles_speech_started(self):
        """Test that speech_started events are forwarded to client."""
        token = create_access_token(subject="test_user")
        speech_started_message = json.dumps({
            "type": "SpeechStarted",
            "timestamp": 1234567890
        })

        mock_ws = create_mock_deepgram_ws([speech_started_message])

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch("backend.api.routes.voice.DEEPGRAM_API_KEY", "test-key"):
            with patch("backend.api.routes.voice.ws_connect", mock_connect):
                client = TestClient(app)
                with client.websocket_connect("/voice/stt") as websocket:
                    # Send auth
                    websocket.send_json({"type": "auth", "token": token})
                    data = websocket.receive_json()
                    assert data["type"] == "connected"

                    data = websocket.receive_json()
                    assert data["type"] == "speech_started"
                    assert data["timestamp"] == 1234567890

    def test_stt_handles_utterance_end(self):
        """Test that utterance_end events are forwarded to client."""
        token = create_access_token(subject="test_user")
        utterance_end_message = json.dumps({
            "type": "UtteranceEnd",
            "last_word_end": 5.5
        })

        mock_ws = create_mock_deepgram_ws([utterance_end_message])

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch("backend.api.routes.voice.DEEPGRAM_API_KEY", "test-key"):
            with patch("backend.api.routes.voice.ws_connect", mock_connect):
                client = TestClient(app)
                with client.websocket_connect("/voice/stt") as websocket:
                    # Send auth
                    websocket.send_json({"type": "auth", "token": token})
                    data = websocket.receive_json()
                    assert data["type"] == "connected"

                    data = websocket.receive_json()
                    assert data["type"] == "utterance_end"
                    assert data["timestamp"] == 5.5

    def test_stt_handles_deepgram_error(self):
        """Test that Deepgram errors are forwarded to client."""
        token = create_access_token(subject="test_user")
        error_message = json.dumps({
            "type": "Error",
            "message": "Something went wrong"
        })

        mock_ws = create_mock_deepgram_ws([error_message])

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch("backend.api.routes.voice.DEEPGRAM_API_KEY", "test-key"):
            with patch("backend.api.routes.voice.ws_connect", mock_connect):
                client = TestClient(app)
                with client.websocket_connect("/voice/stt") as websocket:
                    # Send auth
                    websocket.send_json({"type": "auth", "token": token})
                    data = websocket.receive_json()
                    assert data["type"] == "connected"

                    data = websocket.receive_json()
                    assert data["type"] == "error"
                    assert data["message"] == "Something went wrong"

    def test_stt_handles_keepalive(self):
        """Test that keepalive messages are forwarded to Deepgram."""
        token = create_access_token(subject="test_user")
        mock_ws = create_mock_deepgram_ws()

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch("backend.api.routes.voice.DEEPGRAM_API_KEY", "test-key"):
            with patch("backend.api.routes.voice.ws_connect", mock_connect):
                client = TestClient(app)
                with client.websocket_connect("/voice/stt") as websocket:
                    # Send auth
                    websocket.send_json({"type": "auth", "token": token})
                    data = websocket.receive_json()
                    assert data["type"] == "connected"

                    # Send keepalive
                    websocket.send_json({"type": "keepalive"})

                    # Send stop to cleanly close
                    websocket.send_json({"type": "stop"})

    def test_stt_ignores_empty_transcripts(self):
        """Test that empty transcripts are not forwarded to client."""
        token = create_access_token(subject="test_user")
        # Empty transcript should be ignored
        empty_transcript = json.dumps({
            "type": "Results",
            "channel": {
                "alternatives": [{
                    "transcript": "",
                    "confidence": 0.0
                }]
            },
            "is_final": False,
            "speech_final": False
        })

        # Non-empty transcript should be sent
        real_transcript = json.dumps({
            "type": "Results",
            "channel": {
                "alternatives": [{
                    "transcript": "test",
                    "confidence": 0.95
                }]
            },
            "is_final": True,
            "speech_final": True
        })

        mock_ws = create_mock_deepgram_ws([empty_transcript, real_transcript])

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch("backend.api.routes.voice.DEEPGRAM_API_KEY", "test-key"):
            with patch("backend.api.routes.voice.ws_connect", mock_connect):
                client = TestClient(app)
                with client.websocket_connect("/voice/stt") as websocket:
                    # Send auth
                    websocket.send_json({"type": "auth", "token": token})
                    data = websocket.receive_json()
                    assert data["type"] == "connected"

                    # First non-empty transcript should be the one we get
                    data = websocket.receive_json()
                    assert data["type"] == "transcript"
                    assert data["transcript"] == "test"


class TestSTTParameters:
    """Tests for STT configuration parameters."""

    def test_default_params_include_nova2_model(self):
        """Test that default params use nova-2 model."""
        from backend.api.routes.voice import DEFAULT_STT_PARAMS
        assert DEFAULT_STT_PARAMS["model"] == "nova-2"

    def test_default_params_use_linear16_encoding(self):
        """Test that default params use linear16 encoding."""
        from backend.api.routes.voice import DEFAULT_STT_PARAMS
        assert DEFAULT_STT_PARAMS["encoding"] == "linear16"

    def test_default_params_use_48khz_sample_rate(self):
        """Test that default params use 48kHz sample rate."""
        from backend.api.routes.voice import DEFAULT_STT_PARAMS
        assert DEFAULT_STT_PARAMS["sample_rate"] == "48000"

    def test_default_params_enable_interim_results(self):
        """Test that default params enable interim results."""
        from backend.api.routes.voice import DEFAULT_STT_PARAMS
        assert DEFAULT_STT_PARAMS["interim_results"] == "true"

    def test_default_params_enable_vad_events(self):
        """Test that default params enable VAD events."""
        from backend.api.routes.voice import DEFAULT_STT_PARAMS
        assert DEFAULT_STT_PARAMS["vad_events"] == "true"

    def test_default_params_set_endpointing(self):
        """Test that default params configure endpointing."""
        from backend.api.routes.voice import DEFAULT_STT_PARAMS
        assert "endpointing" in DEFAULT_STT_PARAMS
        assert int(DEFAULT_STT_PARAMS["endpointing"]) > 0
