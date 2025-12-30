"""ARQ Redis pool management.

This module provides access to the ARQ Redis connection pool used for
enqueueing background story generation jobs.
"""

from typing import Optional

from arq import ArqRedis

# Global ARQ Redis pool (set during API startup)
_pool: Optional[ArqRedis] = None


def set_pool(pool: ArqRedis) -> None:
    """Set the ARQ pool. Called during API startup."""
    global _pool
    _pool = pool


def get_pool() -> ArqRedis:
    """Get the ARQ Redis pool. Raises if not initialized."""
    if _pool is None:
        raise RuntimeError(
            "ARQ pool not initialized. Ensure the API server is running."
        )
    return _pool


async def close_pool() -> None:
    """Close the ARQ pool. Called during API shutdown."""
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
