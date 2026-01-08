"""Text-to-speech WebSocket endpoint using Cartesia."""

import base64
import logging
import os
import uuid
from typing import Optional

from cartesia import AsyncCartesia
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from .auth import WebSocketSessionError, authenticated_websocket_session

logger = logging.getLogger(__name__)

router = APIRouter()

# Cartesia TTS configuration
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY", "")
# Default voice - can be overridden per request
DEFAULT_VOICE_ID = os.getenv("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091")

# TTS configuration
MAX_TEXT_LENGTH = 5000  # Max characters per TTS request


def is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError):
        return False


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
                add_timestamps=True,
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
    try:
        async with authenticated_websocket_session(websocket, "TTS"):
            proxy = CartesiaTTSProxy(websocket)

            # Connect to Cartesia
            if not await proxy.connect():
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
                return

            try:
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
                await proxy.close()

    except WebSocketSessionError:
        return  # Auth/rate-limit failure already handled
