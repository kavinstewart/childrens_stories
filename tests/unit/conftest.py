"""Pytest fixtures for API tests."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock

from dotenv import find_dotenv, load_dotenv
from fastapi.testclient import TestClient

# Load environment variables (find_dotenv searches parent directories)
load_dotenv(find_dotenv())

# Set a test API key if not already set (needed for auth)
if not os.getenv("API_KEY"):
    os.environ["API_KEY"] = "test-api-key-for-unit-tests"

# For unit tests with mocks, we don't set DATABASE_URL - the tests use mocked dependencies
# This prevents the app from trying to connect to a real database during startup

# Mock the ARQ pool before importing app to avoid Redis connection during tests
from backend.api import arq_pool as arq_pool_module  # noqa: E402
mock_arq_pool = MagicMock()
mock_arq_pool.enqueue_job = AsyncMock()
mock_arq_pool.aclose = AsyncMock()
arq_pool_module.set_pool(mock_arq_pool)

from backend.api.main import app  # noqa: E402
from backend.api.database.repository import SpreadRegenJobRepository, StoryRepository  # noqa: E402
from backend.api.services.story_service import StoryService  # noqa: E402
from backend.api.auth.tokens import create_access_token  # noqa: E402
from backend.api.dependencies import (  # noqa: E402
    get_repository,
    get_spread_regen_repository,
    get_story_service,
    get_connection,
)
from backend.api import config  # noqa: E402

# Create a test token for authenticated requests
TEST_TOKEN = create_access_token("test-user")


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
    monkeypatch.setattr(config, "STORIES_DIR", temp_data_dir / "stories")
    return temp_data_dir


@pytest.fixture
def mock_connection():
    """Create a mock asyncpg connection for unit tests."""
    conn = MagicMock()
    conn.execute = AsyncMock()
    conn.executemany = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=0)
    # Mock transaction context manager
    conn.transaction = MagicMock()
    conn.transaction.return_value.__aenter__ = AsyncMock()
    conn.transaction.return_value.__aexit__ = AsyncMock()
    return conn


@pytest.fixture
def mock_repository(mock_connection):
    """Create a mock repository for unit tests."""
    repo = AsyncMock(spec=StoryRepository)
    return repo


@pytest.fixture
def mock_regen_repository(mock_connection):
    """Create a mock spread regen job repository for unit tests."""
    repo = AsyncMock(spec=SpreadRegenJobRepository)
    return repo


@pytest.fixture
def mock_service(mock_repository):
    """Create a mock service for unit tests."""
    service = AsyncMock(spec=StoryService)
    return service


class AuthenticatedTestClient:
    """TestClient wrapper that automatically adds auth headers."""

    def __init__(self, client: TestClient, token: str):
        self._client = client
        self._headers = {"Authorization": f"Bearer {token}"}

    def get(self, url, **kwargs):
        kwargs.setdefault("headers", {}).update(self._headers)
        return self._client.get(url, **kwargs)

    def post(self, url, **kwargs):
        kwargs.setdefault("headers", {}).update(self._headers)
        return self._client.post(url, **kwargs)

    def put(self, url, **kwargs):
        kwargs.setdefault("headers", {}).update(self._headers)
        return self._client.put(url, **kwargs)

    def delete(self, url, **kwargs):
        kwargs.setdefault("headers", {}).update(self._headers)
        return self._client.delete(url, **kwargs)

    def patch(self, url, **kwargs):
        kwargs.setdefault("headers", {}).update(self._headers)
        return self._client.patch(url, **kwargs)


@pytest.fixture
def client_with_mocks(mock_repository, mock_regen_repository, mock_service, mock_connection):
    """TestClient with mocked dependencies and auth headers."""

    async def mock_get_connection():
        yield mock_connection

    app.dependency_overrides[get_connection] = mock_get_connection
    app.dependency_overrides[get_repository] = lambda: mock_repository
    app.dependency_overrides[get_spread_regen_repository] = lambda: mock_regen_repository
    app.dependency_overrides[get_story_service] = lambda: mock_service

    with TestClient(app) as base_client:
        client = AuthenticatedTestClient(base_client, TEST_TOKEN)
        yield client, mock_repository, mock_regen_repository, mock_service

    app.dependency_overrides.clear()


@pytest.fixture
def client(mock_config):
    """TestClient with real dependencies but test configuration.

    Note: For integration tests that need a real database,
    you should use a test PostgreSQL instance and set DATABASE_URL
    appropriately.
    """
    with TestClient(app) as client:
        yield client
