"""SQLite database connection management."""

import aiosqlite
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from ..config import DB_PATH

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def init_db() -> None:
    """Initialize database with schema."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        # Enable foreign keys
        await db.execute("PRAGMA foreign_keys = ON")

        # Execute schema
        schema = SCHEMA_PATH.read_text()
        await db.executescript(schema)

        # Migrations: Add columns if they don't exist
        cursor = await db.execute("PRAGMA table_info(stories)")
        columns = [row[1] for row in await cursor.fetchall()]

        if "llm_model" not in columns:
            await db.execute("ALTER TABLE stories ADD COLUMN llm_model TEXT")

        if "progress_json" not in columns:
            await db.execute("ALTER TABLE stories ADD COLUMN progress_json TEXT")

        await db.commit()


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager for database connection."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        yield db
