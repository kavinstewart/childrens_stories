"""FastAPI dependency injection for services and repositories."""

import os
from typing import Annotated

from dotenv import find_dotenv, load_dotenv
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

# Load .env from project root (find_dotenv searches parent directories)
load_dotenv(find_dotenv())

from .database.repository import StoryRepository  # noqa: E402
from .services.story_service import StoryService  # noqa: E402


# API Key authentication
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key() -> str:
    """Get the API key from environment."""
    key = os.getenv("API_KEY")
    if not key:
        raise RuntimeError("API_KEY environment variable not set")
    return key


async def verify_api_key(
    api_key: str = Security(_api_key_header),
) -> str:
    """Verify the API key from request header."""
    expected_key = get_api_key()
    if not api_key or api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key


# Type alias for requiring auth on routes
RequireAuth = Annotated[str, Depends(verify_api_key)]


# Repository - can be overridden in tests
def get_repository() -> StoryRepository:
    """Get a StoryRepository instance."""
    return StoryRepository()


# Service - depends on repository
def get_story_service(
    repo: Annotated[StoryRepository, Depends(get_repository)]
) -> StoryService:
    """Get a StoryService instance with injected repository."""
    return StoryService(repo)


# Type aliases for cleaner route signatures
Repository = Annotated[StoryRepository, Depends(get_repository)]
Service = Annotated[StoryService, Depends(get_story_service)]
