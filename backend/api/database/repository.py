"""Repository for story CRUD operations."""

import json
from datetime import datetime
from typing import Optional
from dataclasses import asdict

from .db import get_db
from ..models.enums import GenerationType, JobStatus
from ..models.responses import (
    StoryResponse,
    StorySpreadResponse,
    StoryOutlineResponse,
    QualityJudgmentResponse,
    CharacterReferenceResponse,
)


class StoryRepository:
    """Repository for story persistence operations."""

    async def create_story(
        self,
        story_id: str,
        goal: str,
        target_age_range: str,
        generation_type: str,
        llm_model: Optional[str] = None,
    ) -> None:
        """Create a new story record in pending status."""
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO stories (id, goal, target_age_range, generation_type, llm_model, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
                """,
                (story_id, goal, target_age_range, generation_type, llm_model),
            )
            await db.commit()

    async def update_status(
        self,
        story_id: str,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update story status and timestamps."""
        async with get_db() as db:
            updates = ["status = ?"]
            params = [status]

            if started_at:
                updates.append("started_at = ?")
                params.append(started_at.isoformat())
            if completed_at:
                updates.append("completed_at = ?")
                params.append(completed_at.isoformat())
            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)

            params.append(story_id)

            await db.execute(
                f"UPDATE stories SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            await db.commit()

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
        async with get_db() as db:
            # Update main story record
            await db.execute(
                """
                UPDATE stories SET
                    title = ?,
                    word_count = ?,
                    spread_count = ?,
                    attempts = ?,
                    is_illustrated = ?,
                    outline_json = ?,
                    judgment_json = ?,
                    status = 'completed',
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    title,
                    word_count,
                    spread_count,
                    attempts,
                    1 if is_illustrated else 0,
                    outline_json,
                    judgment_json,
                    datetime.utcnow().isoformat(),
                    story_id,
                ),
            )

            # Insert spreads
            for spread in spreads:
                await db.execute(
                    """
                    INSERT INTO story_spreads
                    (story_id, spread_number, text, word_count, was_revised,
                     page_turn_note, illustration_prompt, illustration_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        story_id,
                        spread["spread_number"],
                        spread["text"],
                        spread["word_count"],
                        1 if spread.get("was_revised") else 0,
                        spread.get("page_turn_note"),
                        spread.get("illustration_prompt"),
                        spread.get("illustration_path"),
                    ),
                )

            # Insert character references if present
            if character_refs:
                for ref in character_refs:
                    await db.execute(
                        """
                        INSERT INTO character_references
                        (story_id, character_name, character_description, reference_image_path)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            story_id,
                            ref["character_name"],
                            ref.get("character_description"),
                            ref.get("reference_image_path"),
                        ),
                    )

            await db.commit()

    async def get_story(self, story_id: str) -> Optional[StoryResponse]:
        """Get a story by ID with all related data."""
        async with get_db() as db:
            # Get main story
            cursor = await db.execute(
                "SELECT * FROM stories WHERE id = ?",
                (story_id,),
            )
            row = await cursor.fetchone()

            if not row:
                return None

            # Get spreads
            spreads_cursor = await db.execute(
                "SELECT * FROM story_spreads WHERE story_id = ? ORDER BY spread_number",
                (story_id,),
            )
            spreads_rows = await spreads_cursor.fetchall()

            # Get character refs
            refs_cursor = await db.execute(
                "SELECT * FROM character_references WHERE story_id = ?",
                (story_id,),
            )
            refs_rows = await refs_cursor.fetchall()

            return self._row_to_response(row, spreads_rows, refs_rows)

    async def list_stories(
        self,
        limit: int = 20,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> tuple[list[StoryResponse], int]:
        """List stories with pagination and optional status filter."""
        async with get_db() as db:
            # Build query
            where_clause = ""
            params: list = []

            if status:
                where_clause = "WHERE status = ?"
                params.append(status)

            # Get total count
            count_cursor = await db.execute(
                f"SELECT COUNT(*) FROM stories {where_clause}",
                params,
            )
            total = (await count_cursor.fetchone())[0]

            # Get stories
            params.extend([limit, offset])
            cursor = await db.execute(
                f"""
                SELECT * FROM stories {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params,
            )
            rows = await cursor.fetchall()

            # Build responses (without loading pages for list view)
            stories = []
            for row in rows:
                stories.append(self._row_to_response(row, [], []))

            return stories, total

    async def delete_story(self, story_id: str) -> bool:
        """Delete a story and all related data."""
        async with get_db() as db:
            cursor = await db.execute(
                "DELETE FROM stories WHERE id = ?",
                (story_id,),
            )
            await db.commit()
            return cursor.rowcount > 0

    def _row_to_response(
        self,
        row,
        spreads_rows: list,
        refs_rows: list,
    ) -> StoryResponse:
        """Convert database rows to response model."""
        # Parse outline JSON
        outline = None
        if row["outline_json"]:
            outline_data = json.loads(row["outline_json"])
            outline = StoryOutlineResponse(**outline_data)

        # Parse judgment JSON
        judgment = None
        if row["judgment_json"]:
            judgment_data = json.loads(row["judgment_json"])
            judgment = QualityJudgmentResponse(**judgment_data)

        # Convert spreads
        spreads = None
        if spreads_rows:
            spreads = [
                StorySpreadResponse(
                    spread_number=s["spread_number"],
                    text=s["text"],
                    word_count=s["word_count"],
                    was_revised=bool(s["was_revised"]),
                    page_turn_note=s.get("page_turn_note"),
                    illustration_prompt=s["illustration_prompt"],
                    illustration_url=f"/stories/{row['id']}/spreads/{s['spread_number']}/image"
                    if s["illustration_path"]
                    else None,
                )
                for s in spreads_rows
            ]

        # Convert character refs
        character_refs = None
        if refs_rows:
            character_refs = [
                CharacterReferenceResponse(
                    character_name=r["character_name"],
                    character_description=r["character_description"],
                    reference_image_url=f"/stories/{row['id']}/characters/{r['character_name']}/image"
                    if r["reference_image_path"]
                    else None,
                )
                for r in refs_rows
            ]

        # Parse timestamps
        created_at = datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
        started_at = datetime.fromisoformat(row["started_at"]) if row["started_at"] else None
        completed_at = datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None

        return StoryResponse(
            id=row["id"],
            status=JobStatus(row["status"]),
            goal=row["goal"],
            target_age_range=row["target_age_range"],
            generation_type=GenerationType(row["generation_type"]),
            llm_model=row["llm_model"],
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            title=row["title"],
            word_count=row["word_count"],
            spread_count=row["spread_count"],
            attempts=row["attempts"],
            outline=outline,
            spreads=spreads,
            judgment=judgment,
            character_references=character_refs,
            error_message=row["error_message"],
        )
