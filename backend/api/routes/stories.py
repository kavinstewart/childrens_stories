"""Story CRUD endpoints."""

import shutil
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import FileResponse

from ..models.requests import CreateStoryRequest
from ..models.responses import (
    StoryResponse,
    StoryListResponse,
    CreateStoryResponse,
    JobStatus,
)
from ..dependencies import Repository, Service
from ..config import STORIES_DIR

router = APIRouter()


@router.post(
    "/",
    response_model=CreateStoryResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a new story",
    description="Start a new story generation job. Returns immediately with a job ID that can be polled for status.",
)
async def create_story(request: CreateStoryRequest, service: Service):
    """Start a new story generation job."""
    story_id = await service.create_story_job(
        goal=request.goal,
        target_age_range=request.target_age_range,
        generation_type=request.generation_type.value,
        quality_threshold=request.quality_threshold,
        max_attempts=request.max_attempts,
    )

    return CreateStoryResponse(
        id=story_id,
        status=JobStatus.PENDING,
    )


@router.get(
    "/",
    response_model=StoryListResponse,
    summary="List all stories",
    description="Get a paginated list of all stories, optionally filtered by status.",
)
async def list_stories(
    repo: Repository,
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of stories to return"),
    offset: int = Query(default=0, ge=0, description="Number of stories to skip"),
    status: Optional[str] = Query(default=None, description="Filter by status (pending, running, completed, failed)"),
):
    """List all stories with pagination and optional status filter."""
    stories, total = await repo.list_stories(limit=limit, offset=offset, status=status)

    return StoryListResponse(
        stories=stories,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{story_id}",
    response_model=StoryResponse,
    summary="Get a story",
    description="Get a story by ID. Poll this endpoint to check generation status.",
)
async def get_story(story_id: str, repo: Repository):
    """Get a story by ID."""
    story = await repo.get_story(story_id)

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story {story_id} not found",
        )

    return story


@router.get(
    "/{story_id}/spreads/{spread_number}/image",
    summary="Get spread illustration",
    description="Get the illustration image for a specific spread (two facing pages).",
    responses={
        200: {"content": {"image/png": {}}},
        404: {"description": "Image not found"},
    },
)
async def get_spread_image(story_id: str, spread_number: int):
    """Get a spread illustration image."""
    image_path = STORIES_DIR / story_id / "images" / f"spread_{spread_number:02d}.png"

    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image for spread {spread_number} not found",
        )

    return FileResponse(image_path, media_type="image/png")


@router.get(
    "/{story_id}/pages/{page_number}/image",
    summary="Get page illustration (deprecated)",
    description="Deprecated: Use /spreads/{spread_number}/image instead. Get the illustration image for a specific page.",
    responses={
        200: {"content": {"image/png": {}}},
        404: {"description": "Image not found"},
    },
    deprecated=True,
)
async def get_page_image(story_id: str, page_number: int):
    """Get a page illustration image (backwards compatibility alias for spreads)."""
    # Try spread path first (new format), then page path (old format)
    spread_path = STORIES_DIR / story_id / "images" / f"spread_{page_number:02d}.png"
    page_path = STORIES_DIR / story_id / "images" / f"page_{page_number:02d}.png"

    if spread_path.exists():
        return FileResponse(spread_path, media_type="image/png")
    elif page_path.exists():
        return FileResponse(page_path, media_type="image/png")
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image for page/spread {page_number} not found",
        )


@router.get(
    "/{story_id}/characters/{character_name}/image",
    summary="Get character reference image",
    description="Get the reference image for a character.",
    responses={
        200: {"content": {"image/png": {}}},
        404: {"description": "Image not found"},
    },
)
async def get_character_image(story_id: str, character_name: str):
    """Get a character reference image."""
    refs_dir = STORIES_DIR / story_id / "character_refs"

    if not refs_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character references not found for story {story_id}",
        )

    # Find matching file (case-insensitive, partial match)
    for path in refs_dir.glob("*_reference.png"):
        if character_name.lower() in path.stem.lower():
            return FileResponse(path, media_type="image/png")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Character '{character_name}' not found",
    )


@router.delete(
    "/{story_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a story",
    description="Delete a story and all associated files.",
)
async def delete_story(story_id: str, repo: Repository):
    """Delete a story and its files."""
    deleted = await repo.delete_story(story_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story {story_id} not found",
        )

    # Delete files
    story_dir = STORIES_DIR / story_id
    if story_dir.exists():
        shutil.rmtree(story_dir)
