"""Voice routes for streaming STT via Deepgram."""

import asyncio
import base64
import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from websockets import connect as ws_connect
from websockets.exceptions import ConnectionClosed

from ..auth.tokens import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Voice"])

# Rate limiting: track active connections per IP
_active_connections: dict[str, int] = {}
MAX_CONNECTIONS_PER_IP = 3

# Max audio chunk size (64KB should be plenty for audio data)
MAX_AUDIO_CHUNK_SIZE = 64 * 1024


async def authenticate_websocket(websocket: WebSocket) -> bool:
    """Authenticate WebSocket connection via token query param or first message.

    Returns True if authenticated, False otherwise.
    """
    # Try token from query params first
    token = websocket.query_params.get("token")
    if token:
        payload = verify_token(token)
        if payload:
            return True

    # If no token in query, wait for auth message
    try:
        # Give client 5 seconds to send auth message
        message = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=5.0
        )
        if message.get("type") == "auth":
            token = message.get("token")
            if token:
                payload = verify_token(token)
                if payload:
                    return True
    except asyncio.TimeoutError:
        logger.warning("WebSocket auth timeout")
    except Exception as e:
        logger.warning(f"WebSocket auth error: {e}")

    return False

# Deepgram configuration
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"

# Default STT parameters optimized for voice input
DEFAULT_STT_PARAMS = {
    "model": "nova-2",  # Latest Deepgram model
    "language": "en",
    "encoding": "linear16",
    "sample_rate": "48000",
    "channels": "1",
    "punctuate": "true",
    "interim_results": "true",  # Send partial results for responsiveness
    "endpointing": "500",  # End utterance after 500ms silence
    "utterance_end_ms": "1500",  # Full utterance end detection
    "vad_events": "true",  # Voice activity detection events
}


class DeepgramSTTProxy:
    """Proxies audio from client to Deepgram and transcripts back."""

    def __init__(self, client_ws: WebSocket):
        self.client_ws = client_ws
        self.deepgram_ws: Optional[object] = None
        self.is_connected = False
        self._receive_task: Optional[asyncio.Task] = None

    async def connect(self) -> bool:
        """Connect to Deepgram WebSocket."""
        if not DEEPGRAM_API_KEY:
            logger.error("DEEPGRAM_API_KEY not configured")
            await self.client_ws.send_json({
                "type": "error",
                "message": "STT service not configured"
            })
            return False

        # Build URL with query parameters
        params = "&".join(f"{k}={v}" for k, v in DEFAULT_STT_PARAMS.items())
        url = f"{DEEPGRAM_WS_URL}?{params}"

        try:
            self.deepgram_ws = await ws_connect(
                url,
                extra_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"},
            )
            self.is_connected = True
            logger.info("Connected to Deepgram STT")

            # Start receiving transcripts from Deepgram
            self._receive_task = asyncio.create_task(self._receive_from_deepgram())

            await self.client_ws.send_json({
                "type": "connected",
                "message": "STT ready"
            })
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Deepgram: {e}")
            await self.client_ws.send_json({
                "type": "error",
                "message": f"Failed to connect to STT service: {str(e)}"
            })
            return False

    async def _receive_from_deepgram(self):
        """Receive transcripts from Deepgram and forward to client."""
        try:
            async for message in self.deepgram_ws:
                if isinstance(message, str):
                    data = json.loads(message)
                    await self._handle_deepgram_message(data)
        except ConnectionClosed:
            logger.info("Deepgram connection closed")
        except Exception as e:
            logger.error(f"Error receiving from Deepgram: {e}")
        finally:
            self.is_connected = False

    async def _handle_deepgram_message(self, data: dict):
        """Handle a message from Deepgram."""
        msg_type = data.get("type")

        if msg_type == "Results":
            # Extract transcript from results
            channel = data.get("channel", {})
            alternatives = channel.get("alternatives", [])

            if alternatives:
                transcript = alternatives[0].get("transcript", "")
                confidence = alternatives[0].get("confidence", 0)
                is_final = data.get("is_final", False)
                speech_final = data.get("speech_final", False)

                if transcript:  # Only send non-empty transcripts
                    await self.client_ws.send_json({
                        "type": "transcript",
                        "transcript": transcript,
                        "confidence": confidence,
                        "is_final": is_final,
                        "speech_final": speech_final,
                    })

        elif msg_type == "SpeechStarted":
            await self.client_ws.send_json({
                "type": "speech_started",
                "timestamp": data.get("timestamp", 0)
            })

        elif msg_type == "UtteranceEnd":
            await self.client_ws.send_json({
                "type": "utterance_end",
                "timestamp": data.get("last_word_end", 0)
            })

        elif msg_type == "Metadata":
            logger.debug(f"Deepgram metadata: {data}")

        elif msg_type == "Error":
            logger.error(f"Deepgram error: {data}")
            await self.client_ws.send_json({
                "type": "error",
                "message": data.get("message", "Unknown STT error")
            })

    async def send_audio(self, audio_data: bytes):
        """Send audio data to Deepgram."""
        if self.is_connected and self.deepgram_ws:
            try:
                await self.deepgram_ws.send(audio_data)
            except Exception as e:
                logger.error(f"Error sending audio to Deepgram: {e}")

    async def close(self):
        """Close the Deepgram connection."""
        self.is_connected = False

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self.deepgram_ws:
            try:
                # Send close stream message
                await self.deepgram_ws.send(json.dumps({"type": "CloseStream"}))
                await self.deepgram_ws.close()
            except Exception as e:
                logger.debug(f"Error closing Deepgram connection: {e}")

        logger.info("Deepgram STT proxy closed")


@router.websocket("/stt")
async def stt_websocket(websocket: WebSocket):
    """WebSocket endpoint for streaming speech-to-text.

    Protocol:
    - Client sends: {"type": "audio", "data": "<base64 encoded PCM audio>"}
    - Client sends: {"type": "stop"} to end the session
    - Server sends: {"type": "connected", "message": "STT ready"}
    - Server sends: {"type": "transcript", "transcript": "...", "is_final": bool}
    - Server sends: {"type": "speech_started"}
    - Server sends: {"type": "utterance_end"}
    - Server sends: {"type": "error", "message": "..."}
    """
    # Get client IP for rate limiting
    client_ip = websocket.client.host if websocket.client else "unknown"

    # Check rate limit
    current_connections = _active_connections.get(client_ip, 0)
    if current_connections >= MAX_CONNECTIONS_PER_IP:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning(f"Rate limit exceeded for {client_ip}")
        return

    _active_connections[client_ip] = current_connections + 1

    await websocket.accept()
    logger.info(f"STT WebSocket connection accepted from {client_ip}")

    proxy = None
    try:
        # Authenticate the connection
        if not await authenticate_websocket(websocket):
            await websocket.send_json({
                "type": "error",
                "message": "Authentication required"
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        proxy = DeepgramSTTProxy(websocket)

        # Connect to Deepgram
        if not await proxy.connect():
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return

        # Process messages from client
        while True:
            try:
                message = await websocket.receive_json()
                msg_type = message.get("type")

                if msg_type == "audio":
                    # Decode base64 audio and forward to Deepgram
                    audio_b64 = message.get("data", "")
                    if audio_b64:
                        # Validate size before decoding
                        if len(audio_b64) > MAX_AUDIO_CHUNK_SIZE * 4 // 3:  # Base64 is ~4/3 larger
                            logger.warning("Audio chunk too large, skipping")
                            continue
                        try:
                            audio_bytes = base64.b64decode(audio_b64)
                            if len(audio_bytes) > MAX_AUDIO_CHUNK_SIZE:
                                logger.warning("Decoded audio too large, skipping")
                                continue
                            await proxy.send_audio(audio_bytes)
                        except Exception as e:
                            logger.warning(f"Invalid base64 audio data: {e}")

                elif msg_type == "stop":
                    logger.info("Client requested stop")
                    break

                elif msg_type == "keepalive":
                    # Send keepalive to Deepgram
                    if proxy.deepgram_ws:
                        await proxy.deepgram_ws.send(json.dumps({"type": "KeepAlive"}))

            except WebSocketDisconnect:
                logger.info("Client disconnected")
                break

    except Exception as e:
        logger.error(f"STT WebSocket error: {e}")
    finally:
        if proxy:
            await proxy.close()
        logger.info("STT WebSocket session ended")
        # Decrement connection count
        _active_connections[client_ip] = max(0, _active_connections.get(client_ip, 1) - 1)
