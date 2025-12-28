"""Pytest fixtures for API tests."""

import os
import pytest
from unittest.mock import AsyncMock

from dotenv import find_dotenv, load_dotenv
from fastapi.testclient import TestClient

# Load environment variables (find_dotenv searches parent directories)
load_dotenv(find_dotenv())

# Set a test API key if not already set (needed for auth)
if not os.getenv("API_KEY"):
    os.environ["API_KEY"] = "test-api-key-for-unit-tests"

from backend.api.main import app  # noqa: E402
from backend.api.database.db import init_db  # noqa: E402
from backend.api.database.repository import StoryRepository  # noqa: E402
from backend.api.services.story_service import StoryService  # noqa: E402
from backend.api.dependencies import get_repository, get_story_service  # noqa: E402
from backend.api import config  # noqa: E402


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory for tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    stories_dir = data_dir / "stories"
    stories_dir.mkdir()
    return data_dir


@pytest.fixture
def mock_config(temp_data_dir, monkeypatch):
    """Patch config to use temporary directories."""
    monkeypatch.setattr(config, "DATA_DIR", temp_data_dir)
    monkeypatch.setattr(config, "DB_PATH", temp_data_dir / "stories.db")
    monkeypatch.setattr(config, "STORIES_DIR", temp_data_dir / "stories")
    return temp_data_dir


@pytest.fixture
async def initialized_db(mock_config):
    """Initialize a fresh test database."""
    await init_db()
    yield
    # Cleanup handled by temp_data_dir fixture


@pytest.fixture
def mock_repository():
    """Create a mock repository for unit tests."""
    repo = AsyncMock(spec=StoryRepository)
    return repo


@pytest.fixture
def mock_service(mock_repository):
    """Create a mock service for unit tests."""
    service = AsyncMock(spec=StoryService)
    return service


@pytest.fixture
def client_with_mocks(mock_repository, mock_service):
    """TestClient with mocked dependencies."""
    app.dependency_overrides[get_repository] = lambda: mock_repository
    app.dependency_overrides[get_story_service] = lambda: mock_service

    with TestClient(app) as client:
        yield client, mock_repository, mock_service

    app.dependency_overrides.clear()


@pytest.fixture
def client(mock_config):
    """TestClient with real dependencies but test database."""
    with TestClient(app) as client:
        yield client
