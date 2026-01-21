"""Speech-to-text WebSocket endpoint using Deepgram."""

import asyncio
import base64
import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from websockets import connect as ws_connect
from websockets.exceptions import ConnectionClosed

from .auth import (
    MAX_AUDIO_CHUNK_SIZE,
    WebSocketSessionError,
    authenticated_websocket_session,
)

logger = logging.getLogger(__name__)

router = APIRouter()

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
        # Debug counters
        self._audio_chunk_count = 0
        self._total_audio_bytes = 0
        self._transcript_count = 0
        self._deepgram_message_count = 0

    async def connect(self) -> bool:
        """Connect to Deepgram WebSocket."""
        logger.info("[STT] Attempting to connect to Deepgram...")
        if not DEEPGRAM_API_KEY:
            logger.error("[STT] DEEPGRAM_API_KEY not configured")
            await self.client_ws.send_json({
                "type": "error",
                "message": "STT service not configured"
            })
            return False

        # Build URL with query parameters
        params = "&".join(f"{k}={v}" for k, v in DEFAULT_STT_PARAMS.items())
        url = f"{DEEPGRAM_WS_URL}?{params}"
        logger.info(f"[STT] Connecting to Deepgram URL: {DEEPGRAM_WS_URL}")

        try:
            self.deepgram_ws = await ws_connect(
                url,
                additional_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"},
            )
            self.is_connected = True
            logger.info("[STT] Connected to Deepgram STT successfully")

            # Start receiving transcripts from Deepgram
            self._receive_task = asyncio.create_task(self._receive_from_deepgram())

            await self.client_ws.send_json({
                "type": "connected",
                "message": "STT ready"
            })
            return True

        except Exception as e:
            logger.error(f"[STT] Failed to connect to Deepgram: {type(e).__name__}: {e}")
            await self.client_ws.send_json({
                "type": "error",
                "message": f"Failed to connect to STT service: {str(e)}"
            })
            return False

    async def _receive_from_deepgram(self):
        """Receive transcripts from Deepgram and forward to client."""
        logger.info("[STT] Started receiving from Deepgram")
        try:
            async for message in self.deepgram_ws:
                if isinstance(message, str):
                    self._deepgram_message_count += 1
                    data = json.loads(message)
                    await self._handle_deepgram_message(data)
        except ConnectionClosed as e:
            logger.info(f"[STT] Deepgram connection closed: code={e.code} reason={e.reason}. Stats: {self._audio_chunk_count} audio chunks, {self._total_audio_bytes} bytes, {self._transcript_count} transcripts, {self._deepgram_message_count} total messages")
        except Exception as e:
            logger.error(f"[STT] Error receiving from Deepgram: {type(e).__name__}: {e}. Stats: {self._audio_chunk_count} audio chunks, {self._transcript_count} transcripts")
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
                    self._transcript_count += 1
                    logger.info(f"[STT] Transcript #{self._transcript_count}: final={is_final} speechFinal={speech_final} conf={confidence:.2f} \"{transcript[:50]}{'...' if len(transcript) > 50 else ''}\"")
                    await self.client_ws.send_json({
                        "type": "transcript",
                        "transcript": transcript,
                        "confidence": confidence,
                        "is_final": is_final,
                        "speech_final": speech_final,
                    })

        elif msg_type == "SpeechStarted":
            logger.info(f"[STT] SpeechStarted event (after {self._audio_chunk_count} audio chunks)")
            await self.client_ws.send_json({
                "type": "speech_started",
                "timestamp": data.get("timestamp", 0)
            })

        elif msg_type == "UtteranceEnd":
            logger.info(f"[STT] UtteranceEnd event (after {self._transcript_count} transcripts)")
            await self.client_ws.send_json({
                "type": "utterance_end",
                "timestamp": data.get("last_word_end", 0)
            })

        elif msg_type == "Metadata":
            logger.info(f"[STT] Deepgram metadata: request_id={data.get('request_id', 'unknown')}")

        elif msg_type == "Error":
            logger.error(f"[STT] Deepgram error: {data}")
            await self.client_ws.send_json({
                "type": "error",
                "message": data.get("message", "Unknown STT error")
            })

        else:
            logger.debug(f"[STT] Unknown Deepgram message type: {msg_type}")

    async def send_audio(self, audio_data: bytes):
        """Send audio data to Deepgram."""
        if self.is_connected and self.deepgram_ws:
            self._audio_chunk_count += 1
            self._total_audio_bytes += len(audio_data)
            # Log periodically (every 50 chunks) to avoid spam
            if self._audio_chunk_count % 50 == 1:
                logger.info(f"[STT] Audio chunk #{self._audio_chunk_count}: {len(audio_data)} bytes (total: {self._total_audio_bytes} bytes)")
            try:
                await self.deepgram_ws.send(audio_data)
            except Exception as e:
                logger.error(f"[STT] Error sending audio to Deepgram: {type(e).__name__}: {e}")

    async def close(self):
        """Close the Deepgram connection."""
        logger.info(f"[STT] Closing proxy. Session stats: {self._audio_chunk_count} audio chunks, {self._total_audio_bytes} bytes sent, {self._transcript_count} transcripts received, {self._deepgram_message_count} total Deepgram messages")
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
                logger.info("[STT] Deepgram WebSocket closed cleanly")
            except Exception as e:
                logger.debug(f"[STT] Error closing Deepgram connection: {e}")

        logger.info("[STT] Deepgram STT proxy closed")


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
    logger.info("[STT] New WebSocket connection")
    try:
        async with authenticated_websocket_session(websocket, "STT"):
            logger.info("[STT] Client authenticated, creating Deepgram proxy")
            proxy = DeepgramSTTProxy(websocket)

            # Connect to Deepgram
            if not await proxy.connect():
                logger.error("[STT] Failed to connect to Deepgram, closing WebSocket")
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
                return

            client_msg_count = 0
            try:
                # Process messages from client
                while True:
                    try:
                        message = await websocket.receive_json()
                        client_msg_count += 1
                        msg_type = message.get("type")

                        if msg_type == "audio":
                            # Decode base64 audio and forward to Deepgram
                            audio_b64 = message.get("data", "")
                            if audio_b64:
                                # Validate size before decoding
                                if len(audio_b64) > MAX_AUDIO_CHUNK_SIZE * 4 // 3:  # Base64 is ~4/3 larger
                                    logger.warning(f"[STT] Audio chunk too large ({len(audio_b64)} base64 chars), skipping")
                                    continue
                                try:
                                    audio_bytes = base64.b64decode(audio_b64)
                                    if len(audio_bytes) > MAX_AUDIO_CHUNK_SIZE:
                                        logger.warning(f"[STT] Decoded audio too large ({len(audio_bytes)} bytes), skipping")
                                        continue
                                    await proxy.send_audio(audio_bytes)
                                except Exception as e:
                                    logger.warning(f"[STT] Invalid base64 audio data: {e}")

                        elif msg_type == "stop":
                            logger.info(f"[STT] Client requested stop after {client_msg_count} messages")
                            break

                        elif msg_type == "keepalive":
                            logger.debug("[STT] Keepalive received")
                            # Send keepalive to Deepgram
                            if proxy.deepgram_ws:
                                await proxy.deepgram_ws.send(json.dumps({"type": "KeepAlive"}))

                        else:
                            logger.warning(f"[STT] Unknown client message type: {msg_type}")

                    except WebSocketDisconnect:
                        logger.info(f"[STT] Client disconnected after {client_msg_count} messages")
                        break

            except Exception as e:
                logger.error(f"[STT] WebSocket error: {type(e).__name__}: {e}")
            finally:
                await proxy.close()

    except WebSocketSessionError:
        logger.warning("[STT] WebSocket session auth/rate-limit failure")
        return  # Auth/rate-limit failure already handled
