"""FastAPI dependency injection for services and repositories."""

from typing import Annotated, AsyncGenerator

import asyncpg
from dotenv import find_dotenv, load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Load .env from project root (find_dotenv searches parent directories)
load_dotenv(find_dotenv())

from .auth.tokens import verify_token  # noqa: E402
from .database.db import get_pool  # noqa: E402
from .database.repository import SpreadRegenJobRepository, StoryRepository  # noqa: E402
from .services.story_service import StoryService  # noqa: E402

# Security scheme for bearer token authentication
security = HTTPBearer()


# Database connection dependency
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get an async database connection from the pool."""
    pool = get_pool()
    async with pool.acquire() as conn:
        yield conn


# Repository - requires connection
def get_repository(
    conn: Annotated[asyncpg.Connection, Depends(get_connection)]
) -> StoryRepository:
    """Get a StoryRepository instance with injected connection."""
    return StoryRepository(conn)


# Spread regen job repository - requires connection
def get_spread_regen_repository(
    conn: Annotated[asyncpg.Connection, Depends(get_connection)]
) -> SpreadRegenJobRepository:
    """Get a SpreadRegenJobRepository instance with injected connection."""
    return SpreadRegenJobRepository(conn)


# Service - depends on both repositories
def get_story_service(
    repo: Annotated[StoryRepository, Depends(get_repository)],
    regen_repo: Annotated[SpreadRegenJobRepository, Depends(get_spread_regen_repository)],
) -> StoryService:
    """Get a StoryService instance with injected repositories."""
    return StoryService(repo, regen_repo)


# Type aliases for cleaner route signatures
Connection = Annotated[asyncpg.Connection, Depends(get_connection)]
Repository = Annotated[StoryRepository, Depends(get_repository)]
SpreadRegenRepository = Annotated[SpreadRegenJobRepository, Depends(get_spread_regen_repository)]
Service = Annotated[StoryService, Depends(get_story_service)]


# Authentication dependency
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> str:
    """Verify the bearer token and return the user subject.

    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload.get("sub", "unknown")


# Type alias for authenticated user
CurrentUser = Annotated[str, Depends(get_current_user)]
