"""Repository for story CRUD operations using raw asyncpg SQL."""

import json
import random
from datetime import datetime, timezone
from typing import Optional

import asyncpg

from backend.core.types import build_illustration_prompt, DEFAULT_STYLE_PREFIX, DEFAULT_LIGHTING
from ..models.enums import GenerationType, JobStatus
from ..models.responses import (
    CharacterReferenceResponse,
    IllustrationStyleResponse,
    StoryMetadataResponse,
    StoryProgressResponse,
    StoryRecommendationItem,
    StoryResponse,
    StorySpreadResponse,
)


class SpreadRegenJobRepository:
    """Repository for spread regeneration job operations."""

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def create_job(
        self,
        job_id: str,
        story_id: str,
        spread_number: int,
    ) -> None:
        """Create a new spread regeneration job record."""
        await self.conn.execute(
            """
            INSERT INTO spread_regen_jobs (id, story_id, spread_number, status)
            VALUES ($1, $2, $3, 'pending')
            """,
            job_id,
            story_id,
            spread_number,
        )

    async def get_job(self, job_id: str) -> Optional[dict]:
        """Get a spread regeneration job by ID."""
        row = await self.conn.fetchrow(
            "SELECT * FROM spread_regen_jobs WHERE id = $1",
            job_id,
        )
        return dict(row) if row else None

    async def get_active_job(
        self, story_id: str, spread_number: int
    ) -> Optional[dict]:
        """Get an active (pending/running) regeneration job for a spread.

        Jobs are considered stale (not active) if:
        - pending for > 2 minutes (should be picked up quickly)
        - running for > 12 minutes (job_timeout 600s + 2 min buffer)
        """
        row = await self.conn.fetchrow(
            """
            SELECT * FROM spread_regen_jobs
            WHERE story_id = $1 AND spread_number = $2
              AND (
                (status = 'pending' AND created_at > NOW() - INTERVAL '2 minutes')
                OR (status = 'running' AND started_at > NOW() - INTERVAL '12 minutes')
              )
            ORDER BY created_at DESC
            LIMIT 1
            """,
            story_id,
            spread_number,
        )
        return dict(row) if row else None

    async def cleanup_stale_jobs(self) -> int:
        """Mark stale pending/running jobs as failed.

        Returns the number of jobs marked as failed.
        """
        result = await self.conn.execute(
            """
            UPDATE spread_regen_jobs
            SET status = 'failed',
                error_message = 'Job timed out (stale job cleanup)',
                completed_at = NOW()
            WHERE (
                (status = 'pending' AND created_at <= NOW() - INTERVAL '2 minutes')
                OR (status = 'running' AND started_at <= NOW() - INTERVAL '12 minutes')
            )
            """
        )
        # asyncpg returns "UPDATE N" string
        count = int(result.split()[-1]) if result else 0
        return count

    async def update_status(
        self,
        job_id: str,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update spread regeneration job status."""
        await self.conn.execute(
            """
            UPDATE spread_regen_jobs
            SET status = $2,
                started_at = COALESCE($3, started_at),
                completed_at = COALESCE($4, completed_at),
                error_message = COALESCE($5, error_message)
            WHERE id = $1
            """,
            job_id,
            status,
            started_at,
            completed_at,
            error_message,
        )

    async def update_progress(
        self,
        job_id: str,
        progress_json: str,
    ) -> None:
        """Update spread regeneration progress JSON."""
        await self.conn.execute(
            "UPDATE spread_regen_jobs SET progress_json = $2 WHERE id = $1",
            job_id,
            progress_json,
        )

    async def save_regenerated_spread(
        self,
        story_id: str,
        spread_number: int,
        illustration_path: str,
    ) -> None:
        """Update a spread's illustration after successful regeneration."""
        await self.conn.execute(
            """
            UPDATE story_spreads
            SET illustration_path = $3,
                illustration_updated_at = $4
            WHERE story_id = $1 AND spread_number = $2
            """,
            story_id,
            spread_number,
            illustration_path,
            datetime.now(timezone.utc),
        )

    async def get_spread(self, story_id: str, spread_number: int) -> Optional[dict]:
        """Get a single spread by story ID and spread number."""
        row = await self.conn.fetchrow(
            """
            SELECT * FROM story_spreads
            WHERE story_id = $1 AND spread_number = $2
            """,
            story_id,
            spread_number,
        )
        return dict(row) if row else None


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
        # Build query conditionally based on status filter
        where_clause = "WHERE status = $1" if status else ""
        params: list = [status] if status else []

        # Get total count
        count_query = f"SELECT COUNT(*) FROM stories {where_clause}"
        total = await self.conn.fetchval(count_query, *params)

        # Get paginated results
        param_offset = len(params)
        list_query = f"""
            SELECT * FROM stories
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_offset + 1} OFFSET ${param_offset + 2}
        """
        stories = await self.conn.fetch(list_query, *params, limit, offset)

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

    def _parse_metadata(self, story: asyncpg.Record) -> Optional[StoryMetadataResponse]:
        """Parse outline_json into StoryMetadataResponse."""
        if not story["outline_json"]:
            return None
        metadata_data = json.loads(story["outline_json"])
        return StoryMetadataResponse(**metadata_data)

    def _parse_progress(self, story: asyncpg.Record) -> Optional[StoryProgressResponse]:
        """Parse progress_json into StoryProgressResponse."""
        if not story["progress_json"]:
            return None
        progress_data = json.loads(story["progress_json"])
        if progress_data.get("updated_at"):
            progress_data["updated_at"] = datetime.fromisoformat(progress_data["updated_at"])
        return StoryProgressResponse(**progress_data)

    def _build_spread_responses(
        self,
        story_id: str,
        spreads: list[asyncpg.Record],
        metadata: Optional[StoryMetadataResponse],
    ) -> list[StorySpreadResponse]:
        """Convert spread records to StorySpreadResponse list.

        Note: We compute composed_prompt here rather than storing it or using a
        service layer. It's a debug-only field and build_illustration_prompt is
        a pure function. If this grows more complex, consider a response mapper.
        """
        style = metadata.illustration_style if metadata else None
        setting = metadata.setting if metadata else ""

        return [
            StorySpreadResponse(
                spread_number=s["spread_number"],
                text=s["text"],
                word_count=s["word_count"],
                was_revised=s["was_revised"],
                page_turn_note=s["page_turn_note"],
                illustration_prompt=s["illustration_prompt"],
                illustration_url=f"/stories/{story_id}/spreads/{s['spread_number']}/image"
                if s["illustration_path"]
                else None,
                illustration_updated_at=s.get("illustration_updated_at"),
                composed_prompt=build_illustration_prompt(
                    illustration_prompt=s["illustration_prompt"] or "",
                    setting=setting,
                    style_prefix=style.prompt_prefix if style else DEFAULT_STYLE_PREFIX,
                    lighting=style.lighting_direction if style and style.lighting_direction else DEFAULT_LIGHTING,
                ) if s["illustration_prompt"] else None,
            )
            for s in spreads
        ]

    def _build_character_ref_responses(
        self,
        story_id: str,
        char_refs: list[asyncpg.Record],
    ) -> list[CharacterReferenceResponse]:
        """Convert character reference records to CharacterReferenceResponse list."""
        return [
            CharacterReferenceResponse(
                character_name=r["character_name"],
                character_description=r["character_description"],
                reference_image_url=f"/stories/{story_id}/characters/{r['character_name']}/image"
                if r["reference_image_path"]
                else None,
            )
            for r in char_refs
        ]

    def _record_to_response(
        self,
        story: asyncpg.Record,
        spreads: Optional[list[asyncpg.Record]] = None,
        char_refs: Optional[list[asyncpg.Record]] = None,
    ) -> StoryResponse:
        """Convert asyncpg Record to response model."""
        metadata = self._parse_metadata(story)
        progress = self._parse_progress(story)

        spread_responses = (
            self._build_spread_responses(story["id"], spreads, metadata)
            if spreads else None
        )
        char_ref_responses = (
            self._build_character_ref_responses(story["id"], char_refs)
            if char_refs else None
        )

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
            metadata=metadata,
            spreads=spread_responses,
            character_references=char_ref_responses,
            progress=progress,
            error_message=story["error_message"],
        )
