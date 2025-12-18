"""FastAPI dependency injection for services and repositories."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from .database.repository import StoryRepository
from .services.story_service import StoryService


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
