"""Repository for VLM evaluation logging and retrieval using raw asyncpg SQL."""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import asyncpg
from PIL import Image

from ..config import DATA_DIR
from ...core.modules.vlm_judge import DetailedCheckResult


# Directory for storing evaluation images
VLM_EVALS_DIR = DATA_DIR / "vlm_evals"


class VLMEvalRepository:
    """Repository for VLM evaluation records."""

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    @staticmethod
    def _ensure_dirs():
        """Ensure evaluation directories exist."""
        VLM_EVALS_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _save_image(image: Image.Image, eval_id: str, suffix: str = "") -> str:
        """Save image and return relative path."""
        VLMEvalRepository._ensure_dirs()
        filename = f"{eval_id}{suffix}.png"
        path = VLM_EVALS_DIR / filename
        image.save(path, "PNG")
        return f"vlm_evals/{filename}"

    async def log_evaluation(
        self,
        image: Image.Image,
        prompt: str,
        result: DetailedCheckResult,
        raw_response: str,
        model: str,
        character_refs: Optional[list[tuple[str, Image.Image, str]]] = None,
        story_id: Optional[str] = None,
        spread_number: Optional[int] = None,
        check_text_free: bool = True,
        check_characters: bool = True,
        check_composition: bool = True,
    ) -> str:
        """
        Log a VLM evaluation with all context for later annotation.

        Returns:
            The evaluation ID
        """
        eval_id = str(uuid.uuid4())[:8]

        # Save the evaluated image
        image_path = self._save_image(image, eval_id, "_image")

        # Save character reference images if present
        ref_paths = []
        if character_refs:
            for i, ref in enumerate(character_refs):
                if len(ref) == 3:
                    name, ref_img, _ = ref
                else:
                    name, ref_img = ref
                ref_path = self._save_image(
                    ref_img, eval_id, f"_ref_{i}_{name.replace(' ', '_')}"
                )
                ref_paths.append(ref_path)

        await self.conn.execute(
            """
            INSERT INTO vlm_evaluations (
                id, story_id, spread_number, prompt, image_path, character_ref_paths,
                check_text_free, check_characters, check_composition,
                vlm_model, vlm_raw_response, vlm_overall_pass, vlm_text_free,
                vlm_character_match_score, vlm_scene_accuracy_score,
                vlm_composition_score, vlm_style_score, vlm_issues
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
            """,
            eval_id,
            story_id,
            spread_number,
            prompt,
            image_path,
            json.dumps(ref_paths) if ref_paths else None,
            check_text_free,
            check_characters,
            check_composition,
            model,
            raw_response,
            result.overall_pass,
            result.text_free,
            result.character_match_score,
            result.scene_accuracy_score,
            result.composition_score,
            result.style_score,
            json.dumps(result.issues) if result.issues else None,
        )

        return eval_id

    async def get_evaluation(self, eval_id: str) -> Optional[dict]:
        """Get a single evaluation by ID."""
        row = await self.conn.fetchrow(
            "SELECT * FROM vlm_evaluations WHERE id = $1",
            eval_id,
        )
        if row:
            return self._record_to_dict(row)
        return None

    async def list_evaluations(
        self,
        unannotated_only: bool = False,
        story_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List evaluations with optional filters."""
        conditions = []
        params = []
        param_idx = 1

        if unannotated_only:
            conditions.append("human_verdict IS NULL")

        if story_id:
            conditions.append(f"story_id = ${param_idx}")
            params.append(story_id)
            param_idx += 1

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        params.extend([limit, offset])
        query = f"""
            SELECT * FROM vlm_evaluations
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """

        rows = await self.conn.fetch(query, *params)
        return [self._record_to_dict(r) for r in rows]

    async def annotate(
        self,
        eval_id: str,
        human_verdict: bool,
        human_notes: Optional[str] = None,
    ) -> bool:
        """Add human annotation to an evaluation."""
        result = await self.conn.execute(
            """
            UPDATE vlm_evaluations
            SET human_verdict = $2, human_notes = $3, annotated_at = $4
            WHERE id = $1
            """,
            eval_id,
            human_verdict,
            human_notes,
            datetime.now(timezone.utc),
        )
        # Result is like "UPDATE 1" or "UPDATE 0"
        return result.split()[-1] != "0"

    async def get_stats(self) -> dict:
        """Get annotation statistics."""
        total = await self.conn.fetchval(
            "SELECT COUNT(*) FROM vlm_evaluations"
        )
        annotated = await self.conn.fetchval(
            "SELECT COUNT(*) FROM vlm_evaluations WHERE human_verdict IS NOT NULL"
        )
        agreement = await self.conn.fetchval(
            "SELECT COUNT(*) FROM vlm_evaluations WHERE human_verdict = vlm_overall_pass"
        )

        total = total or 0
        annotated = annotated or 0
        agreement = agreement or 0

        return {
            "total": total,
            "annotated": annotated,
            "unannotated": total - annotated,
            "agreement_count": agreement,
            "agreement_rate": agreement / annotated if annotated > 0 else None,
        }

    async def export_for_gepa(self) -> list[dict]:
        """Export annotated evaluations for GEPA optimization."""
        rows = await self.conn.fetch(
            """
            SELECT * FROM vlm_evaluations
            WHERE human_verdict IS NOT NULL
            ORDER BY created_at
            """
        )
        return [self._record_to_dict(r) for r in rows]

    def _record_to_dict(self, row: asyncpg.Record) -> dict:
        """Convert asyncpg Record to dictionary."""
        return {
            "id": row["id"],
            "story_id": row["story_id"],
            "spread_number": row["spread_number"],
            "prompt": row["prompt"],
            "image_path": row["image_path"],
            "character_ref_paths": row["character_ref_paths"],
            "check_text_free": row["check_text_free"],
            "check_characters": row["check_characters"],
            "check_composition": row["check_composition"],
            "vlm_model": row["vlm_model"],
            "vlm_raw_response": row["vlm_raw_response"],
            "vlm_overall_pass": row["vlm_overall_pass"],
            "vlm_text_free": row["vlm_text_free"],
            "vlm_character_match_score": row["vlm_character_match_score"],
            "vlm_scene_accuracy_score": row["vlm_scene_accuracy_score"],
            "vlm_composition_score": row["vlm_composition_score"],
            "vlm_style_score": row["vlm_style_score"],
            "vlm_issues": row["vlm_issues"],
            "human_verdict": row["human_verdict"],
            "human_notes": row["human_notes"],
            "annotated_at": row["annotated_at"].isoformat() if row["annotated_at"] else None,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
