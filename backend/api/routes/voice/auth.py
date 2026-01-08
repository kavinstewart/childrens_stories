"""WebSocket authentication and rate limiting for voice endpoints."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import WebSocket, status

from ...auth.tokens import verify_token

logger = logging.getLogger(__name__)

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


class WebSocketSessionError(Exception):
    """Raised when WebSocket session setup fails."""
    pass


@asynccontextmanager
async def authenticated_websocket_session(websocket: WebSocket, endpoint_name: str):
    """Context manager for authenticated, rate-limited WebSocket sessions.

    Handles:
    - Connection acceptance and logging
    - Authentication
    - Rate limiting per IP
    - Connection count cleanup

    Yields the client IP on success, raises WebSocketSessionError on failure.
    """
    client_ip = websocket.client.host if websocket.client else "unknown"

    await websocket.accept()
    logger.info(f"{endpoint_name} WebSocket connection accepted from {client_ip}")

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
        raise WebSocketSessionError("Authentication failed")

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
        raise WebSocketSessionError("Rate limit exceeded")

    _active_connections[client_ip] = current_connections + 1

    try:
        yield client_ip
    finally:
        # Decrement connection count
        _active_connections[client_ip] = max(0, _active_connections.get(client_ip, 1) - 1)
        logger.info(f"{endpoint_name} WebSocket session ended")
