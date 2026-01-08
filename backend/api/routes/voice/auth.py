"""WebSocket authentication and rate limiting for voice endpoints."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import WebSocket, status

from ...auth.tokens import verify_token

logger = logging.getLogger(__name__)

# Rate limiting: track active connections per IP
_active_connections: dict[str, int] = {}
_rate_limit_lock = asyncio.Lock()
MAX_CONNECTIONS_PER_IP = 3

# Max audio chunk size (64KB should be plenty for audio data)
MAX_AUDIO_CHUNK_SIZE = 64 * 1024

# Whether to trust X-Forwarded-For/X-Real-IP headers for client IP detection.
# Only enable this when running behind a trusted reverse proxy that sets these headers.
# Set TRUST_PROXY_HEADERS=true in production when behind nginx/caddy/etc.
TRUST_PROXY_HEADERS = os.getenv("TRUST_PROXY_HEADERS", "").lower() in ("true", "1", "yes")


def get_client_ip(websocket: WebSocket) -> str:
    """Get the real client IP, accounting for reverse proxies.

    Only checks X-Forwarded-For and X-Real-IP headers if TRUST_PROXY_HEADERS
    is enabled. This prevents IP spoofing when the app is directly exposed.
    """
    if TRUST_PROXY_HEADERS:
        # Check X-Forwarded-For first (may contain multiple IPs: client, proxy1, proxy2)
        forwarded_for = websocket.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP (simpler single-IP header)
        real_ip = websocket.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

    # Fall back to direct connection IP
    return websocket.client.host if websocket.client else "unknown"


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
    - Rate limiting per IP (thread-safe with asyncio.Lock)
    - Connection count cleanup

    Yields the client IP on success, raises WebSocketSessionError on failure.
    """
    client_ip = get_client_ip(websocket)

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

    # Check and increment rate limit atomically to prevent race conditions
    async with _rate_limit_lock:
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
        # Decrement connection count atomically
        async with _rate_limit_lock:
            _active_connections[client_ip] = max(0, _active_connections.get(client_ip, 1) - 1)
        logger.info(f"{endpoint_name} WebSocket session ended")
