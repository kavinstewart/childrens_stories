"""Repository for VLM evaluation logging and retrieval using SQLAlchemy ORM."""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import VLMEvaluation
from ..config import DATA_DIR
from ...core.modules.vlm_judge import DetailedCheckResult


# Directory for storing evaluation images
VLM_EVALS_DIR = DATA_DIR / "vlm_evals"


class VLMEvalRepository:
    """Repository for VLM evaluation records."""

    def __init__(self, session: AsyncSession):
        self.session = session

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

        evaluation = VLMEvaluation(
            id=eval_id,
            story_id=story_id,
            spread_number=spread_number,
            prompt=prompt,
            image_path=image_path,
            character_ref_paths=json.dumps(ref_paths) if ref_paths else None,
            check_text_free=check_text_free,
            check_characters=check_characters,
            check_composition=check_composition,
            vlm_model=model,
            vlm_raw_response=raw_response,
            vlm_overall_pass=result.overall_pass,
            vlm_text_free=result.text_free,
            vlm_character_match_score=result.character_match_score,
            vlm_scene_accuracy_score=result.scene_accuracy_score,
            vlm_composition_score=result.composition_score,
            vlm_style_score=result.style_score,
            vlm_issues=json.dumps(result.issues) if result.issues else None,
        )
        self.session.add(evaluation)
        await self.session.flush()

        return eval_id

    async def get_evaluation(self, eval_id: str) -> Optional[dict]:
        """Get a single evaluation by ID."""
        result = await self.session.execute(
            select(VLMEvaluation).where(VLMEvaluation.id == eval_id)
        )
        evaluation = result.scalar_one_or_none()
        if evaluation:
            return self._model_to_dict(evaluation)
        return None

    async def list_evaluations(
        self,
        unannotated_only: bool = False,
        story_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List evaluations with optional filters."""
        query = select(VLMEvaluation)

        if unannotated_only:
            query = query.where(VLMEvaluation.human_verdict.is_(None))

        if story_id:
            query = query.where(VLMEvaluation.story_id == story_id)

        query = query.order_by(VLMEvaluation.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(query)
        evaluations = result.scalars().all()
        return [self._model_to_dict(e) for e in evaluations]

    async def annotate(
        self,
        eval_id: str,
        human_verdict: bool,
        human_notes: Optional[str] = None,
    ) -> bool:
        """Add human annotation to an evaluation."""
        result = await self.session.execute(
            select(VLMEvaluation).where(VLMEvaluation.id == eval_id)
        )
        evaluation = result.scalar_one_or_none()

        if not evaluation:
            return False

        evaluation.human_verdict = human_verdict
        evaluation.human_notes = human_notes
        evaluation.annotated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    async def get_stats(self) -> dict:
        """Get annotation statistics."""
        total_result = await self.session.execute(
            select(func.count()).select_from(VLMEvaluation)
        )
        total = total_result.scalar() or 0

        annotated_result = await self.session.execute(
            select(func.count())
            .select_from(VLMEvaluation)
            .where(VLMEvaluation.human_verdict.is_not(None))
        )
        annotated = annotated_result.scalar() or 0

        # For agreement, we need to compare human_verdict with vlm_overall_pass
        agreement_result = await self.session.execute(
            select(func.count())
            .select_from(VLMEvaluation)
            .where(VLMEvaluation.human_verdict == VLMEvaluation.vlm_overall_pass)
        )
        agreement = agreement_result.scalar() or 0

        return {
            "total": total,
            "annotated": annotated,
            "unannotated": total - annotated,
            "agreement_count": agreement,
            "agreement_rate": agreement / annotated if annotated > 0 else None,
        }

    async def export_for_gepa(self) -> list[dict]:
        """Export annotated evaluations for GEPA optimization."""
        result = await self.session.execute(
            select(VLMEvaluation)
            .where(VLMEvaluation.human_verdict.is_not(None))
            .order_by(VLMEvaluation.created_at)
        )
        evaluations = result.scalars().all()
        return [self._model_to_dict(e) for e in evaluations]

    def _model_to_dict(self, evaluation: VLMEvaluation) -> dict:
        """Convert SQLAlchemy model to dictionary."""
        return {
            "id": evaluation.id,
            "story_id": evaluation.story_id,
            "spread_number": evaluation.spread_number,
            "prompt": evaluation.prompt,
            "image_path": evaluation.image_path,
            "character_ref_paths": evaluation.character_ref_paths,
            "check_text_free": evaluation.check_text_free,
            "check_characters": evaluation.check_characters,
            "check_composition": evaluation.check_composition,
            "vlm_model": evaluation.vlm_model,
            "vlm_raw_response": evaluation.vlm_raw_response,
            "vlm_overall_pass": evaluation.vlm_overall_pass,
            "vlm_text_free": evaluation.vlm_text_free,
            "vlm_character_match_score": evaluation.vlm_character_match_score,
            "vlm_scene_accuracy_score": evaluation.vlm_scene_accuracy_score,
            "vlm_composition_score": evaluation.vlm_composition_score,
            "vlm_style_score": evaluation.vlm_style_score,
            "vlm_issues": evaluation.vlm_issues,
            "human_verdict": evaluation.human_verdict,
            "human_notes": evaluation.human_notes,
            "annotated_at": evaluation.annotated_at.isoformat() if evaluation.annotated_at else None,
            "created_at": evaluation.created_at.isoformat() if evaluation.created_at else None,
        }
