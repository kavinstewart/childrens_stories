"""WebSocket authentication for voice endpoints."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import WebSocket, status

from ...auth.tokens import verify_token

logger = logging.getLogger(__name__)

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


class WebSocketSessionError(Exception):
    """Raised when WebSocket session setup fails."""
    pass


@asynccontextmanager
async def authenticated_websocket_session(websocket: WebSocket, endpoint_name: str):
    """Context manager for authenticated WebSocket sessions.

    Handles connection acceptance, logging, and authentication.
    Raises WebSocketSessionError on auth failure.

    Note: Per-user rate limiting will be added when subscription system exists.
    For now, JWT auth is sufficient protection since only logged-in users can connect.
    """
    await websocket.accept()
    logger.info(f"{endpoint_name} WebSocket connection accepted")

    if not await authenticate_websocket(websocket):
        try:
            await websocket.send_json({
                "type": "error",
                "code": "auth_required",
                "message": "Authentication required"
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        except Exception:
            pass  # Connection already closed
        raise WebSocketSessionError("Authentication failed")

    try:
        yield
    finally:
        logger.info(f"{endpoint_name} WebSocket session ended")
