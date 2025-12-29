"""Repository for story CRUD operations using SQLAlchemy ORM."""

import json
import random
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import CharacterReference, Story, StorySpread
from ..models.enums import GenerationType, JobStatus
from ..models.responses import (
    CharacterReferenceResponse,
    QualityJudgmentResponse,
    StoryOutlineResponse,
    StoryProgressResponse,
    StoryRecommendationItem,
    StoryResponse,
    StorySpreadResponse,
)


class StoryRepository:
    """Repository for story persistence operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_story(
        self,
        story_id: str,
        goal: str,
        target_age_range: str,
        generation_type: str,
        llm_model: Optional[str] = None,
    ) -> None:
        """Create a new story record in pending status."""
        story = Story(
            id=story_id,
            goal=goal,
            target_age_range=target_age_range,
            generation_type=generation_type,
            llm_model=llm_model,
            status="pending",
        )
        self.session.add(story)
        await self.session.flush()

    async def update_status(
        self,
        story_id: str,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update story status and timestamps."""
        result = await self.session.execute(select(Story).where(Story.id == story_id))
        story = result.scalar_one_or_none()

        if story:
            story.status = status
            if started_at:
                story.started_at = started_at
            if completed_at:
                story.completed_at = completed_at
            if error_message is not None:
                story.error_message = error_message
            await self.session.flush()

    async def update_progress(self, story_id: str, progress_json: str) -> None:
        """Update story progress JSON."""
        result = await self.session.execute(select(Story).where(Story.id == story_id))
        story = result.scalar_one_or_none()

        if story:
            story.progress_json = progress_json
            await self.session.flush()

    async def save_completed_story(
        self,
        story_id: str,
        title: str,
        word_count: int,
        spread_count: int,
        attempts: int,
        is_illustrated: bool,
        outline_json: str,
        judgment_json: Optional[str],
        spreads: list[dict],
        character_refs: Optional[list[dict]] = None,
    ) -> None:
        """Save completed story data."""
        result = await self.session.execute(select(Story).where(Story.id == story_id))
        story = result.scalar_one_or_none()

        if not story:
            return

        # Update main story record
        story.title = title
        story.word_count = word_count
        story.spread_count = spread_count
        story.attempts = attempts
        story.is_illustrated = is_illustrated
        story.outline_json = outline_json
        story.judgment_json = judgment_json
        story.status = "completed"
        story.completed_at = datetime.now(timezone.utc)

        # Insert spreads
        for spread_data in spreads:
            spread = StorySpread(
                story_id=story_id,
                spread_number=spread_data["spread_number"],
                text=spread_data["text"],
                word_count=spread_data.get("word_count"),
                was_revised=spread_data.get("was_revised", False),
                page_turn_note=spread_data.get("page_turn_note"),
                illustration_prompt=spread_data.get("illustration_prompt"),
                illustration_path=spread_data.get("illustration_path"),
            )
            self.session.add(spread)

        # Insert character references if present
        if character_refs:
            for ref_data in character_refs:
                ref = CharacterReference(
                    story_id=story_id,
                    character_name=ref_data["character_name"],
                    character_description=ref_data.get("character_description"),
                    reference_image_path=ref_data.get("reference_image_path"),
                )
                self.session.add(ref)

        await self.session.flush()

    async def get_story(self, story_id: str) -> Optional[StoryResponse]:
        """Get a story by ID with all related data."""
        result = await self.session.execute(
            select(Story)
            .options(selectinload(Story.spreads), selectinload(Story.character_references))
            .where(Story.id == story_id)
        )
        story = result.scalar_one_or_none()

        if not story:
            return None

        return self._model_to_response(story)

    async def list_stories(
        self,
        limit: int = 20,
        offset: int = 0,
        status: Optional[str] = "completed",
    ) -> tuple[list[StoryResponse], int]:
        """List stories with pagination and optional status filter."""
        # Build base query
        query = select(Story)

        if status:
            query = query.where(Story.status == status)

        # Get total count
        count_query = select(func.count()).select_from(Story)
        if status:
            count_query = count_query.where(Story.status == status)
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Get stories (without loading relationships for list view)
        query = query.order_by(Story.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        stories = result.scalars().all()

        return [self._model_to_response(s, include_relations=False) for s in stories], total

    async def delete_story(self, story_id: str) -> bool:
        """Delete a story and all related data."""
        result = await self.session.execute(delete(Story).where(Story.id == story_id))
        await self.session.flush()
        return result.rowcount > 0

    async def get_recommendations(
        self,
        exclude_story_id: str,
        limit: int = 4,
    ) -> list[StoryRecommendationItem]:
        """Get random story recommendations, excluding a specific story."""
        result = await self.session.execute(
            select(Story.id, Story.title, Story.goal, Story.generation_type)
            .where(Story.status == "completed")
            .where(Story.id != exclude_story_id)
        )
        rows = result.all()

        if not rows:
            return []

        # Shuffle and take first N
        rows = list(rows)
        random.shuffle(rows)
        selected = rows[:limit]

        return [
            StoryRecommendationItem(
                id=row.id,
                title=row.title,
                goal=row.goal,
                cover_url=f"/stories/{row.id}/spreads/1/image",
                is_illustrated=row.generation_type == "illustrated",
            )
            for row in selected
        ]

    def _model_to_response(
        self,
        story: Story,
        include_relations: bool = True,
    ) -> StoryResponse:
        """Convert SQLAlchemy model to response model."""
        # Parse outline JSON
        outline = None
        if story.outline_json:
            outline_data = json.loads(story.outline_json)
            outline = StoryOutlineResponse(**outline_data)

        # Parse judgment JSON
        judgment = None
        if story.judgment_json:
            judgment_data = json.loads(story.judgment_json)
            judgment = QualityJudgmentResponse(**judgment_data)

        # Convert spreads
        spreads = None
        if include_relations and story.spreads:
            spreads = [
                StorySpreadResponse(
                    spread_number=s.spread_number,
                    text=s.text,
                    word_count=s.word_count,
                    was_revised=s.was_revised,
                    page_turn_note=s.page_turn_note,
                    illustration_prompt=s.illustration_prompt,
                    illustration_url=f"/stories/{story.id}/spreads/{s.spread_number}/image"
                    if s.illustration_path
                    else None,
                )
                for s in story.spreads
            ]

        # Convert character refs
        character_refs = None
        if include_relations and story.character_references:
            character_refs = [
                CharacterReferenceResponse(
                    character_name=r.character_name,
                    character_description=r.character_description,
                    reference_image_url=f"/stories/{story.id}/characters/{r.character_name}/image"
                    if r.reference_image_path
                    else None,
                )
                for r in story.character_references
            ]

        # Parse progress JSON
        progress = None
        if story.progress_json:
            progress_data = json.loads(story.progress_json)
            if progress_data.get("updated_at"):
                progress_data["updated_at"] = datetime.fromisoformat(progress_data["updated_at"])
            progress = StoryProgressResponse(**progress_data)

        return StoryResponse(
            id=story.id,
            status=JobStatus(story.status),
            goal=story.goal,
            target_age_range=story.target_age_range,
            generation_type=GenerationType(story.generation_type),
            llm_model=story.llm_model,
            created_at=story.created_at,
            started_at=story.started_at,
            completed_at=story.completed_at,
            title=story.title,
            word_count=story.word_count,
            spread_count=story.spread_count,
            attempts=story.attempts,
            outline=outline,
            spreads=spreads,
            judgment=judgment,
            character_references=character_refs,
            progress=progress,
            error_message=story.error_message,
        )
