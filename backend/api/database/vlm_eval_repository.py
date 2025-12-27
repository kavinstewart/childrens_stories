"""Repository for VLM evaluation logging and retrieval."""

import json
import uuid
from datetime import datetime
from typing import Optional

from PIL import Image

from .db import get_db
from ..config import DATA_DIR
from ...core.modules.vlm_judge import DetailedCheckResult


# Directory for storing evaluation images
VLM_EVALS_DIR = DATA_DIR / "vlm_evals"


class VLMEvalRepository:
    """Repository for VLM evaluation records."""

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

    @staticmethod
    async def log_evaluation(
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
        image_path = VLMEvalRepository._save_image(image, eval_id, "_image")

        # Save character reference images if present
        ref_paths = []
        if character_refs:
            for i, ref in enumerate(character_refs):
                if len(ref) == 3:
                    name, ref_img, _ = ref
                else:
                    name, ref_img = ref
                ref_path = VLMEvalRepository._save_image(
                    ref_img, eval_id, f"_ref_{i}_{name.replace(' ', '_')}"
                )
                ref_paths.append(ref_path)

        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO vlm_evaluations (
                    id, story_id, spread_number,
                    prompt, image_path, character_ref_paths,
                    check_text_free, check_characters, check_composition,
                    vlm_model, vlm_raw_response, vlm_overall_pass,
                    vlm_text_free, vlm_character_match_score,
                    vlm_scene_accuracy_score, vlm_composition_score,
                    vlm_style_score, vlm_issues
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    eval_id,
                    story_id,
                    spread_number,
                    prompt,
                    image_path,
                    json.dumps(ref_paths) if ref_paths else None,
                    int(check_text_free),
                    int(check_characters),
                    int(check_composition),
                    model,
                    raw_response,
                    int(result.overall_pass),
                    int(result.text_free),
                    result.character_match_score,
                    result.scene_accuracy_score,
                    result.composition_score,
                    result.style_score,
                    json.dumps(result.issues) if result.issues else None,
                ),
            )
            await db.commit()

        return eval_id

    @staticmethod
    async def get_evaluation(eval_id: str) -> Optional[dict]:
        """Get a single evaluation by ID."""
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM vlm_evaluations WHERE id = ?",
                (eval_id,),
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    @staticmethod
    async def list_evaluations(
        unannotated_only: bool = False,
        story_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List evaluations with optional filters."""
        conditions = []
        params = []

        if unannotated_only:
            conditions.append("human_verdict IS NULL")

        if story_id:
            conditions.append("story_id = ?")
            params.append(story_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.extend([limit, offset])

        async with get_db() as db:
            cursor = await db.execute(
                f"""
                SELECT * FROM vlm_evaluations
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params,
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    async def annotate(
        eval_id: str,
        human_verdict: bool,
        human_notes: Optional[str] = None,
    ) -> bool:
        """Add human annotation to an evaluation."""
        async with get_db() as db:
            cursor = await db.execute(
                """
                UPDATE vlm_evaluations
                SET human_verdict = ?, human_notes = ?, annotated_at = ?
                WHERE id = ?
                """,
                (
                    int(human_verdict),
                    human_notes,
                    datetime.utcnow().isoformat(),
                    eval_id,
                ),
            )
            await db.commit()
            return cursor.rowcount > 0

    @staticmethod
    async def get_stats() -> dict:
        """Get annotation statistics."""
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN human_verdict IS NOT NULL THEN 1 ELSE 0 END) as annotated,
                    SUM(CASE WHEN human_verdict = vlm_overall_pass THEN 1 ELSE 0 END) as agreement
                FROM vlm_evaluations
                """
            )
            row = await cursor.fetchone()
            total = row["total"] or 0
            annotated = row["annotated"] or 0
            agreement = row["agreement"] or 0

            return {
                "total": total,
                "annotated": annotated,
                "unannotated": total - annotated,
                "agreement_count": agreement,
                "agreement_rate": agreement / annotated if annotated > 0 else None,
            }

    @staticmethod
    async def export_for_gepa() -> list[dict]:
        """Export annotated evaluations for GEPA optimization."""
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT * FROM vlm_evaluations
                WHERE human_verdict IS NOT NULL
                ORDER BY created_at
                """
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
