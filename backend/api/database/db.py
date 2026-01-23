"""PostgreSQL database connection management using asyncpg."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional

import asyncpg

from ..config import DATABASE_URL, get_dsn


# Global pool - initialized in lifespan handler, not at module import
_pool: Optional[asyncpg.Pool] = None


async def create_db_pool(
    min_size: int = 2,
    max_size: int = 10,
    command_timeout: int = 60,
) -> asyncpg.Pool:
    """Create a connection pool with standard settings.

    This factory function can be used by both FastAPI (via init_pool) and
    ARQ worker (directly) to create pools with consistent configuration.

    Args:
        min_size: Minimum connections to keep open
        max_size: Maximum connections allowed
        command_timeout: Query timeout in seconds

    Returns:
        Configured asyncpg connection pool

    Raises:
        RuntimeError: If DATABASE_URL is not configured
    """
    dsn = get_dsn()
    if not dsn:
        raise RuntimeError(
            "Database not configured. Set DATABASE_URL environment variable "
            "to a PostgreSQL connection string."
        )
    return await asyncpg.create_pool(
        dsn,
        min_size=min_size,
        max_size=max_size,
        command_timeout=command_timeout,
    )


def get_pool() -> asyncpg.Pool:
    """Get the connection pool. Raises if not initialized."""
    if _pool is None:
        raise RuntimeError(
            "Database pool not initialized. Ensure init_pool() is called in lifespan."
        )
    return _pool


async def init_pool() -> asyncpg.Pool:
    """Create and store the connection pool. Call this in FastAPI lifespan."""
    global _pool
    _pool = await create_db_pool(min_size=2, max_size=10)
    return _pool


async def close_pool() -> None:
    """Close the connection pool. Call this in FastAPI lifespan shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def init_db() -> None:
    """Initialize database - run schema.sql to create tables."""
    pool = get_pool()
    schema_path = Path(__file__).parent / "schema.sql"

    async with pool.acquire() as conn:
        schema_sql = schema_path.read_text()
        await conn.execute(schema_sql)


@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get a connection from the pool."""
    pool = get_pool()
    async with pool.acquire() as conn:
        yield conn
