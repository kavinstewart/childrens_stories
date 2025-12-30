"""Repository for story CRUD operations using raw asyncpg SQL."""

import json
import random
from datetime import datetime, timezone
from typing import Optional

import asyncpg

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

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def create_story(
        self,
        story_id: str,
        goal: str,
        target_age_range: str,
        generation_type: str,
        llm_model: Optional[str] = None,
    ) -> None:
        """Create a new story record in pending status."""
        # is_illustrated defaults based on generation_type
        is_illustrated = generation_type == "illustrated"
        await self.conn.execute(
            """
            INSERT INTO stories (id, goal, target_age_range, generation_type, llm_model, status, is_illustrated)
            VALUES ($1, $2, $3, $4, $5, 'pending', $6)
            """,
            story_id,
            goal,
            target_age_range,
            generation_type,
            llm_model,
            is_illustrated,
        )

    async def update_status(
        self,
        story_id: str,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update story status and timestamps."""
        await self.conn.execute(
            """
            UPDATE stories
            SET status = $2,
                started_at = COALESCE($3, started_at),
                completed_at = COALESCE($4, completed_at),
                error_message = COALESCE($5, error_message)
            WHERE id = $1
            """,
            story_id,
            status,
            started_at,
            completed_at,
            error_message,
        )

    async def update_progress(self, story_id: str, progress_json: str) -> None:
        """Update story progress JSON."""
        await self.conn.execute(
            "UPDATE stories SET progress_json = $2 WHERE id = $1",
            story_id,
            progress_json,
        )

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
        """Save completed story data in a transaction."""
        async with self.conn.transaction():
            # Update main story record
            await self.conn.execute(
                """
                UPDATE stories
                SET title = $2,
                    word_count = $3,
                    spread_count = $4,
                    attempts = $5,
                    is_illustrated = $6,
                    outline_json = $7,
                    judgment_json = $8,
                    status = 'completed',
                    completed_at = $9
                WHERE id = $1
                """,
                story_id,
                title,
                word_count,
                spread_count,
                attempts,
                is_illustrated,
                outline_json,
                judgment_json,
                datetime.now(timezone.utc),
            )

            # Batch insert spreads
            spread_data = [
                (
                    story_id,
                    s["spread_number"],
                    s["text"],
                    s.get("word_count"),
                    s.get("was_revised", False),
                    s.get("page_turn_note"),
                    s.get("illustration_prompt"),
                    s.get("illustration_path"),
                )
                for s in spreads
            ]
            await self.conn.executemany(
                """
                INSERT INTO story_spreads
                    (story_id, spread_number, text, word_count, was_revised,
                     page_turn_note, illustration_prompt, illustration_path)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                spread_data,
            )

            # Batch insert character references if present
            if character_refs:
                ref_data = [
                    (
                        story_id,
                        r["character_name"],
                        r.get("character_description"),
                        r.get("reference_image_path"),
                    )
                    for r in character_refs
                ]
                await self.conn.executemany(
                    """
                    INSERT INTO character_references
                        (story_id, character_name, character_description, reference_image_path)
                    VALUES ($1, $2, $3, $4)
                    """,
                    ref_data,
                )

    async def get_story(self, story_id: str) -> Optional[StoryResponse]:
        """Get a story by ID with all related data."""
        # Fetch story
        story = await self.conn.fetchrow(
            "SELECT * FROM stories WHERE id = $1",
            story_id,
        )
        if not story:
            return None

        # Fetch spreads
        spreads = await self.conn.fetch(
            """
            SELECT * FROM story_spreads
            WHERE story_id = $1
            ORDER BY spread_number
            """,
            story_id,
        )

        # Fetch character references
        char_refs = await self.conn.fetch(
            "SELECT * FROM character_references WHERE story_id = $1",
            story_id,
        )

        return self._record_to_response(story, spreads, char_refs)

    async def list_stories(
        self,
        limit: int = 20,
        offset: int = 0,
        status: Optional[str] = "completed",
    ) -> tuple[list[StoryResponse], int]:
        """List stories with pagination and optional status filter."""
        # Get total count
        if status:
            total = await self.conn.fetchval(
                "SELECT COUNT(*) FROM stories WHERE status = $1",
                status,
            )
            stories = await self.conn.fetch(
                """
                SELECT * FROM stories
                WHERE status = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                status,
                limit,
                offset,
            )
        else:
            total = await self.conn.fetchval("SELECT COUNT(*) FROM stories")
            stories = await self.conn.fetch(
                """
                SELECT * FROM stories
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )

        return [self._record_to_response(s) for s in stories], total or 0

    async def delete_story(self, story_id: str) -> bool:
        """Delete a story and all related data (cascades via FK)."""
        result = await self.conn.execute(
            "DELETE FROM stories WHERE id = $1",
            story_id,
        )
        # Result is like "DELETE 1" or "DELETE 0"
        return result.split()[-1] != "0"

    async def get_recommendations(
        self,
        exclude_story_id: str,
        limit: int = 4,
    ) -> list[StoryRecommendationItem]:
        """Get random story recommendations, excluding a specific story."""
        rows = await self.conn.fetch(
            """
            SELECT id, title, goal, generation_type
            FROM stories
            WHERE status = 'completed' AND id != $1
            """,
            exclude_story_id,
        )

        if not rows:
            return []

        # Shuffle and take first N
        rows = list(rows)
        random.shuffle(rows)
        selected = rows[:limit]

        return [
            StoryRecommendationItem(
                id=row["id"],
                title=row["title"],
                goal=row["goal"],
                cover_url=f"/stories/{row['id']}/spreads/1/image",
                is_illustrated=row["generation_type"] == "illustrated",
            )
            for row in selected
        ]

    def _record_to_response(
        self,
        story: asyncpg.Record,
        spreads: Optional[list[asyncpg.Record]] = None,
        char_refs: Optional[list[asyncpg.Record]] = None,
    ) -> StoryResponse:
        """Convert asyncpg Record to response model."""
        # Parse outline JSON
        outline = None
        if story["outline_json"]:
            outline_data = json.loads(story["outline_json"])
            outline = StoryOutlineResponse(**outline_data)

        # Parse judgment JSON
        judgment = None
        if story["judgment_json"]:
            judgment_data = json.loads(story["judgment_json"])
            judgment = QualityJudgmentResponse(**judgment_data)

        # Convert spreads
        spread_responses = None
        if spreads:
            spread_responses = [
                StorySpreadResponse(
                    spread_number=s["spread_number"],
                    text=s["text"],
                    word_count=s["word_count"],
                    was_revised=s["was_revised"],
                    page_turn_note=s["page_turn_note"],
                    illustration_prompt=s["illustration_prompt"],
                    illustration_url=f"/stories/{story['id']}/spreads/{s['spread_number']}/image"
                    if s["illustration_path"]
                    else None,
                )
                for s in spreads
            ]

        # Convert character refs
        char_ref_responses = None
        if char_refs:
            char_ref_responses = [
                CharacterReferenceResponse(
                    character_name=r["character_name"],
                    character_description=r["character_description"],
                    reference_image_url=f"/stories/{story['id']}/characters/{r['character_name']}/image"
                    if r["reference_image_path"]
                    else None,
                )
                for r in char_refs
            ]

        # Parse progress JSON
        progress = None
        if story["progress_json"]:
            progress_data = json.loads(story["progress_json"])
            if progress_data.get("updated_at"):
                progress_data["updated_at"] = datetime.fromisoformat(progress_data["updated_at"])
            progress = StoryProgressResponse(**progress_data)

        return StoryResponse(
            id=story["id"],
            status=JobStatus(story["status"]),
            goal=story["goal"],
            target_age_range=story["target_age_range"],
            generation_type=GenerationType(story["generation_type"]),
            llm_model=story["llm_model"],
            created_at=story["created_at"],
            started_at=story["started_at"],
            completed_at=story["completed_at"],
            title=story["title"],
            word_count=story["word_count"],
            spread_count=story["spread_count"],
            attempts=story["attempts"],
            outline=outline,
            spreads=spread_responses,
            judgment=judgment,
            character_references=char_ref_responses,
            progress=progress,
            error_message=story["error_message"],
        )
