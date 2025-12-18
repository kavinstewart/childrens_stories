"""Pytest fixtures for API tests."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.database.db import init_db
from backend.api.database.repository import StoryRepository
from backend.api.services.story_service import StoryService
from backend.api.dependencies import get_repository, get_story_service
from backend.api import config


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
