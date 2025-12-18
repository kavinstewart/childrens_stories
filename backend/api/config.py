"""API configuration constants.

Single source of truth for paths and settings used across the API layer.
"""

from pathlib import Path

# Base directories
API_DIR = Path(__file__).parent
BACKEND_DIR = API_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = PROJECT_DIR / "data"

# Database
DB_PATH = DATA_DIR / "stories.db"

# Story file storage
STORIES_DIR = DATA_DIR / "stories"

# Job manager settings
MAX_CONCURRENT_JOBS = 2
