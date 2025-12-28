"""FastAPI dependency injection for services and repositories."""

from typing import Annotated

from dotenv import find_dotenv, load_dotenv
from fastapi import Depends

# Load .env from project root (find_dotenv searches parent directories)
load_dotenv(find_dotenv())

from .database.repository import StoryRepository  # noqa: E402
from .services.story_service import StoryService  # noqa: E402


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
