"""PostgreSQL database connection management using asyncpg."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional

import asyncpg

from ..config import DATABASE_URL


# Global pool - initialized in lifespan handler, not at module import
_pool: Optional[asyncpg.Pool] = None


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
    if not DATABASE_URL:
        raise RuntimeError(
            "Database not configured. Set DATABASE_URL environment variable "
            "to a PostgreSQL connection string."
        )

    # Convert SQLAlchemy-style URL to asyncpg format
    # postgresql+asyncpg://... -> postgresql://...
    dsn = DATABASE_URL.replace("+asyncpg", "")

    _pool = await asyncpg.create_pool(
        dsn,
        min_size=2,
        max_size=10,
        command_timeout=60,
    )
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
