"""API configuration constants.

Single source of truth for paths and settings used across the API layer.
"""

import os
from pathlib import Path

# Base directories
API_DIR = Path(__file__).parent
BACKEND_DIR = API_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = PROJECT_DIR / "data"

# Database configuration
# PostgreSQL connection URL (required for production)
# Format: postgresql+asyncpg://user:password@host:port/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "")


def get_dsn() -> str:
    """Get asyncpg-compatible DSN from DATABASE_URL.

    Converts SQLAlchemy-style URL (postgresql+asyncpg://...) to
    plain asyncpg format (postgresql://...).
    """
    return DATABASE_URL.replace("+asyncpg", "")

# Story file storage
STORIES_DIR = DATA_DIR / "stories"

# Story generation defaults
DEFAULT_TARGET_AGE_RANGE = "4-7"
DEFAULT_GENERATION_TYPE = "illustrated"
