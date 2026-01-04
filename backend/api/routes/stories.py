"""Story CRUD endpoints."""

import shutil
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import FileResponse

from ..models.requests import CreateStoryRequest, RegenerateSpreadRequest
from ..models.responses import (
    StoryResponse,
    StoryListResponse,
    CreateStoryResponse,
    StoryRecommendationsResponse,
    RegenerateSpreadResponse,
    JobStatus,
)
from ..dependencies import Repository, SpreadRegenRepository, Service, CurrentUser
from ..config import STORIES_DIR

router = APIRouter()


@router.post(
    "/",
    response_model=CreateStoryResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a new story",
    description="Start a new story generation job. Returns immediately with a job ID that can be polled for status.",
)
async def create_story(request: CreateStoryRequest, service: Service, user: CurrentUser):
    """Start a new story generation job."""
    story_id = await service.create_story_job(goal=request.goal)

    return CreateStoryResponse(
        id=story_id,
        status=JobStatus.PENDING,
    )


@router.get(
    "/",
    response_model=StoryListResponse,
    summary="List all stories",
    description="Get a paginated list of stories. By default returns only completed stories.",
)
async def list_stories(
    repo: Repository,
    user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of stories to return"),
    offset: int = Query(default=0, ge=0, description="Number of stories to skip"),
    status: Optional[str] = Query(default="completed", description="Filter by status (pending, running, completed, failed, or 'all' for no filter)"),
):
    """List stories with pagination. Defaults to completed stories only."""
    # Allow 'all' to bypass the filter
    filter_status = None if status == "all" else status
    stories, total = await repo.list_stories(limit=limit, offset=offset, status=filter_status)

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
async def get_story(story_id: str, repo: Repository, user: CurrentUser):
    """Get a story by ID."""
    story = await repo.get_story(story_id)

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story {story_id} not found",
        )

    return story


@router.get(
    "/{story_id}/recommendations",
    response_model=StoryRecommendationsResponse,
    summary="Get story recommendations",
    description="Get recommended stories to read next, excluding the current story.",
)
async def get_recommendations(
    story_id: str,
    repo: Repository,
    user: CurrentUser,
    limit: int = Query(default=4, ge=1, le=10, description="Number of recommendations"),
):
    """Get story recommendations for the completion screen."""
    recommendations = await repo.get_recommendations(
        exclude_story_id=story_id,
        limit=limit,
    )

    return StoryRecommendationsResponse(recommendations=recommendations)


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
    """Get a spread illustration image (no auth - images accessed via unguessable UUID)."""
    image_path = STORIES_DIR / story_id / "images" / f"spread_{spread_number:02d}.png"

    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image for spread {spread_number} not found",
        )

    return FileResponse(image_path, media_type="image/png")


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
    """Get a character reference image (no auth - images accessed via unguessable UUID)."""
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


@router.post(
    "/{story_id}/spreads/{spread_number}/regenerate",
    response_model=RegenerateSpreadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Regenerate spread illustration",
    description="Start regenerating the illustration for a specific spread. Returns immediately with a job ID.",
)
async def regenerate_spread(
    story_id: str,
    spread_number: int,
    request: RegenerateSpreadRequest,
    repo: Repository,
    regen_repo: SpreadRegenRepository,
    service: Service,
    user: CurrentUser,
):
    """Start regeneration of a single spread illustration."""
    # Verify story exists
    story = await repo.get_story(story_id)
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story {story_id} not found",
        )

    # Verify story is illustrated
    if not story.is_illustrated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot regenerate illustration for non-illustrated story",
        )

    # Verify spread exists
    spread = await regen_repo.get_spread(story_id, spread_number)
    if not spread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spread {spread_number} not found in story {story_id}",
        )

    # Check if already regenerating
    active_job = await regen_repo.get_active_job(story_id, spread_number)
    if active_job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Spread {spread_number} is already being regenerated (job {active_job['id']})",
        )

    # Create regeneration job
    job_id = await service.regenerate_spread_job(
        story_id=story_id,
        spread_number=spread_number,
        custom_prompt=request.prompt,
    )

    return RegenerateSpreadResponse(
        job_id=job_id,
        story_id=story_id,
        spread_number=spread_number,
        status=JobStatus.PENDING,
    )


@router.delete(
    "/{story_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a story",
    description="Delete a story and all associated files.",
)
async def delete_story(story_id: str, repo: Repository, user: CurrentUser):
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
