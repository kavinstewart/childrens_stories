"""Voice routes for streaming STT via Deepgram and TTS via Cartesia."""

import asyncio
import base64
import json
import logging
import os
import uuid
from typing import Optional

import dspy
from cartesia import AsyncCartesia
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, HTTPException
from pydantic import BaseModel
from websockets import connect as ws_connect
from websockets.exceptions import ConnectionClosed

from ..auth.tokens import verify_token
from ..dependencies import CurrentUser
from ...config.llm import get_inference_lm

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

# Cartesia TTS configuration
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY", "")
# Default voice - can be overridden per request
DEFAULT_VOICE_ID = os.getenv("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091")  # Default Cartesia voice

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
                additional_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"},
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

    await websocket.accept()
    logger.info(f"STT WebSocket connection accepted from {client_ip}")

    # Authenticate BEFORE counting against rate limit
    if not await authenticate_websocket(websocket):
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Authentication required"
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        except Exception:
            pass  # Connection already closed
        return

    # Check rate limit only after successful auth
    current_connections = _active_connections.get(client_ip, 0)
    if current_connections >= MAX_CONNECTIONS_PER_IP:
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Too many connections"
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        except Exception:
            pass  # Connection already closed
        logger.warning(f"Rate limit exceeded for {client_ip}")
        return

    _active_connections[client_ip] = current_connections + 1

    proxy = None
    try:
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


# TTS configuration
MAX_TEXT_LENGTH = 5000  # Max characters per TTS request


class CartesiaTTSProxy:
    """Streams text to Cartesia TTS and audio back to client."""

    def __init__(self, client_ws: WebSocket):
        self.client_ws = client_ws
        self.cartesia_client: Optional[AsyncCartesia] = None
        self.ws = None
        self.is_connected = False

    async def connect(self) -> bool:
        """Connect to Cartesia TTS WebSocket."""
        if not CARTESIA_API_KEY:
            logger.error("CARTESIA_API_KEY not configured")
            await self.client_ws.send_json({
                "type": "error",
                "message": "TTS service not configured"
            })
            return False

        try:
            self.cartesia_client = AsyncCartesia(api_key=CARTESIA_API_KEY)
            self.ws = await self.cartesia_client.tts.websocket()
            self.is_connected = True
            logger.info("Connected to Cartesia TTS")

            await self.client_ws.send_json({
                "type": "connected",
                "message": "TTS ready"
            })
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Cartesia: {e}")
            await self.client_ws.send_json({
                "type": "error",
                "message": f"Failed to connect to TTS service: {str(e)}"
            })
            return False

    async def synthesize(self, text: str, voice_id: Optional[str] = None, context_id: Optional[str] = None):
        """Synthesize text to speech and stream audio chunks to client."""
        if not self.is_connected or not self.ws:
            return

        voice = voice_id or DEFAULT_VOICE_ID
        ctx_id = context_id or str(uuid.uuid4())

        try:
            # Stream audio from Cartesia
            logger.info(f"Starting TTS synthesis: {text[:50]}... (voice={voice})")
            logger.debug(f"TTS context_id: {ctx_id}")
            output_stream = await self.ws.send(
                model_id="sonic-3",
                transcript=text,
                voice={"mode": "id", "id": voice},
                context_id=ctx_id,
                output_format={
                    "container": "raw",
                    "encoding": "pcm_s16le",
                    "sample_rate": 24000,
                },
                stream=True,
            )
            chunk_count = 0
            async for output in output_stream:
                chunk_count += 1
                # Cartesia SDK output has .audio attribute containing the audio bytes
                audio_data = getattr(output, "audio", None)
                if audio_data:
                    await self.client_ws.send_json({
                        "type": "audio",
                        "data": base64.b64encode(audio_data).decode() if isinstance(audio_data, bytes) else audio_data,
                        "context_id": ctx_id,
                    })

                # Forward word timestamps if available
                word_timestamps = getattr(output, "word_timestamps", None)
                if word_timestamps:
                    words = getattr(word_timestamps, "words", [])
                    await self.client_ws.send_json({
                        "type": "timestamps",
                        "words": words,
                        "context_id": ctx_id,
                    })

            # Signal synthesis complete
            logger.debug(f"TTS synthesis complete, sent {chunk_count} chunks")
            await self.client_ws.send_json({
                "type": "done",
                "context_id": ctx_id,
            })

        except Exception as e:
            logger.exception(f"TTS synthesis error: {type(e).__name__}: {e}")
            try:
                await self.client_ws.send_json({
                    "type": "error",
                    "message": f"TTS synthesis failed: {type(e).__name__}: {str(e)}",
                    "context_id": ctx_id,
                })
            except Exception as send_err:
                logger.error(f"Failed to send error to client: {send_err}")

    async def close(self):
        """Close the Cartesia connection."""
        self.is_connected = False
        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                logger.debug(f"Error closing Cartesia connection: {e}")
        if self.cartesia_client:
            try:
                await self.cartesia_client.close()
            except Exception as e:
                logger.debug(f"Error closing Cartesia client: {e}")
        logger.info("Cartesia TTS proxy closed")


def is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError):
        return False


@router.websocket("/tts")
async def tts_websocket(websocket: WebSocket):
    """WebSocket endpoint for streaming text-to-speech.

    Protocol:
    - Client sends: {"type": "auth", "token": "<jwt>"}
    - Client sends: {"type": "synthesize", "text": "...", "voice_id": "...", "context_id": "..."}
    - Client sends: {"type": "stop"} to end the session
    - Server sends: {"type": "connected", "message": "TTS ready"}
    - Server sends: {"type": "audio", "data": "<base64 PCM>", "context_id": "..."}
    - Server sends: {"type": "timestamps", "words": [...], "context_id": "..."}
    - Server sends: {"type": "done", "context_id": "..."}
    - Server sends: {"type": "error", "message": "..."}
    """
    # Get client IP for rate limiting
    client_ip = websocket.client.host if websocket.client else "unknown"

    await websocket.accept()
    logger.info(f"TTS WebSocket connection accepted from {client_ip}")

    # Authenticate BEFORE counting against rate limit
    if not await authenticate_websocket(websocket):
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Authentication required"
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        except Exception:
            pass  # Connection already closed
        return

    # Check rate limit only after successful auth
    current_connections = _active_connections.get(client_ip, 0)
    if current_connections >= MAX_CONNECTIONS_PER_IP:
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Too many connections"
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        except Exception:
            pass  # Connection already closed
        logger.warning(f"Rate limit exceeded for {client_ip}")
        return

    _active_connections[client_ip] = current_connections + 1

    proxy = None
    try:
        proxy = CartesiaTTSProxy(websocket)

        # Connect to Cartesia
        if not await proxy.connect():
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return

        # Process messages from client
        while True:
            try:
                message = await websocket.receive_json()
                msg_type = message.get("type")

                if msg_type == "synthesize":
                    text = message.get("text", "")
                    if not text:
                        await websocket.send_json({
                            "type": "error",
                            "message": "No text provided"
                        })
                        continue

                    # Validate text length
                    if len(text) > MAX_TEXT_LENGTH:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Text too long (max {MAX_TEXT_LENGTH} chars)"
                        })
                        continue

                    voice_id = message.get("voice_id")
                    # Validate voice_id if provided
                    if voice_id and not is_valid_uuid(voice_id):
                        await websocket.send_json({
                            "type": "error",
                            "message": "Invalid voice_id format (must be UUID)"
                        })
                        continue

                    context_id = message.get("context_id")
                    await proxy.synthesize(text, voice_id, context_id)

                elif msg_type == "stop":
                    logger.info("Client requested stop")
                    break

            except WebSocketDisconnect:
                logger.info("Client disconnected")
                break

    except Exception as e:
        logger.error(f"TTS WebSocket error: {e}")
    finally:
        if proxy:
            await proxy.close()
        logger.info("TTS WebSocket session ended")
        # Decrement connection count
        _active_connections[client_ip] = max(0, _active_connections.get(client_ip, 1) - 1)


# =============================================================================
# Transcript Summarization (LLM-based)
# =============================================================================

class SummarizeRequest(BaseModel):
    """Request body for /voice/summarize endpoint."""
    transcript: str


class SummarizeResponse(BaseModel):
    """Response body for /voice/summarize endpoint."""
    goal: str
    summary: str


class TranscriptSummarizer(dspy.Signature):
    """Extract a clear story goal from a voice transcript.

    The user has spoken a story idea aloud, possibly with filler words, repetition,
    or rambling. Extract the core story concept and create a clear, concise goal
    that can be used to generate a children's picture book.
    """

    transcript: str = dspy.InputField(
        desc="Raw voice transcript, may contain filler words, repetition, or unclear speech"
    )
    goal: str = dspy.OutputField(
        desc="A clear, concise story goal (1-2 sentences) suitable for generating a children's picture book. Should capture the main theme, characters, and lesson if any."
    )
    summary: str = dspy.OutputField(
        desc="A friendly, conversational summary to read back to the user confirming what story will be created. Start with 'I'll create' or similar."
    )


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_transcript(
    request: SummarizeRequest,
    current_user: CurrentUser,
) -> SummarizeResponse:
    """
    Summarize a voice transcript into a clear story goal.

    Uses an LLM to extract the core story idea from potentially rambling
    or unclear speech, returning both a clean goal for story generation
    and a friendly summary for TTS confirmation.
    """
    transcript = request.transcript.strip()

    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript cannot be empty")

    logger.info(f"Summarizing transcript: {transcript[:100]}...")

    try:
        # Use DSPy to extract goal and summary
        lm = get_inference_lm()
        summarizer = dspy.Predict(TranscriptSummarizer)

        with dspy.context(lm=lm):
            result = summarizer(transcript=transcript)

        logger.info(f"Extracted goal: {result.goal}")

        return SummarizeResponse(
            goal=result.goal,
            summary=result.summary,
        )

    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to summarize transcript")
