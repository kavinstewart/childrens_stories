"""FastAPI dependency injection for services and repositories."""

from typing import Annotated, AsyncGenerator

from dotenv import find_dotenv, load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

# Load .env from project root (find_dotenv searches parent directories)
load_dotenv(find_dotenv())

from .auth.tokens import verify_token  # noqa: E402
from .database.db import async_session_factory  # noqa: E402
from .database.repository import StoryRepository  # noqa: E402
from .database.vlm_eval_repository import VLMEvalRepository  # noqa: E402
from .services.story_service import StoryService  # noqa: E402

# Security scheme for bearer token authentication
security = HTTPBearer()


# Database session dependency
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Repository - requires session
def get_repository(
    session: Annotated[AsyncSession, Depends(get_session)]
) -> StoryRepository:
    """Get a StoryRepository instance with injected session."""
    return StoryRepository(session)


# VLM Eval Repository - requires session
def get_vlm_eval_repository(
    session: Annotated[AsyncSession, Depends(get_session)]
) -> VLMEvalRepository:
    """Get a VLMEvalRepository instance with injected session."""
    return VLMEvalRepository(session)


# Service - depends on repository
def get_story_service(
    repo: Annotated[StoryRepository, Depends(get_repository)]
) -> StoryService:
    """Get a StoryService instance with injected repository."""
    return StoryService(repo)


# Type aliases for cleaner route signatures
Session = Annotated[AsyncSession, Depends(get_session)]
Repository = Annotated[StoryRepository, Depends(get_repository)]
VLMEvalRepo = Annotated[VLMEvalRepository, Depends(get_vlm_eval_repository)]
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
