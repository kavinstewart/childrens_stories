"""Admin routes for VLM evaluation annotation and GEPA optimization."""

import base64
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..database.vlm_eval_repository import VLMEvalRepository, VLM_EVALS_DIR
from ..config import DATA_DIR


router = APIRouter()


class AnnotateRequest(BaseModel):
    """Request to annotate an evaluation."""
    human_verdict: bool  # True = pass, False = fail
    human_notes: Optional[str] = None


class EvalSummary(BaseModel):
    """Summary of an evaluation for list view."""
    id: str
    story_id: Optional[str]
    spread_number: Optional[int]
    prompt: str
    vlm_overall_pass: bool
    human_verdict: Optional[bool]
    created_at: str


class EvalDetail(BaseModel):
    """Full evaluation detail including images."""
    id: str
    story_id: Optional[str]
    spread_number: Optional[int]
    prompt: str

    # Images as base64
    image_base64: Optional[str]
    character_ref_base64: list[str]

    # Check flags
    check_text_free: bool
    check_characters: bool
    check_composition: bool

    # VLM output
    vlm_model: str
    vlm_raw_response: Optional[str]
    vlm_overall_pass: bool
    vlm_text_free: Optional[bool]
    vlm_character_match_score: Optional[int]
    vlm_scene_accuracy_score: Optional[int]
    vlm_composition_score: Optional[int]
    vlm_style_score: Optional[int]
    vlm_issues: list[str]

    # Human annotation
    human_verdict: Optional[bool]
    human_notes: Optional[str]
    annotated_at: Optional[str]

    created_at: str


class StatsResponse(BaseModel):
    """Annotation statistics."""
    total: int
    annotated: int
    unannotated: int
    agreement_count: int
    agreement_rate: Optional[float]


def _load_image_as_base64(relative_path: str) -> Optional[str]:
    """Load an image from disk and return as base64."""
    if not relative_path:
        return None

    full_path = DATA_DIR / relative_path
    if not full_path.exists():
        return None

    with open(full_path, "rb") as f:
        data = f.read()

    return base64.b64encode(data).decode("utf-8")


def _row_to_summary(row: dict) -> EvalSummary:
    """Convert database row to EvalSummary."""
    return EvalSummary(
        id=row["id"],
        story_id=row.get("story_id"),
        spread_number=row.get("spread_number"),
        prompt=row["prompt"][:100] + "..." if len(row["prompt"]) > 100 else row["prompt"],
        vlm_overall_pass=bool(row.get("vlm_overall_pass", 1)),
        human_verdict=bool(row["human_verdict"]) if row.get("human_verdict") is not None else None,
        created_at=row["created_at"],
    )


def _row_to_detail(row: dict) -> EvalDetail:
    """Convert database row to EvalDetail with images."""
    # Load main image
    image_base64 = _load_image_as_base64(row.get("image_path", ""))

    # Load character reference images
    ref_paths = json.loads(row.get("character_ref_paths") or "[]")
    ref_base64 = [
        b64 for path in ref_paths
        if (b64 := _load_image_as_base64(path)) is not None
    ]

    # Parse issues
    issues = json.loads(row.get("vlm_issues") or "[]")

    return EvalDetail(
        id=row["id"],
        story_id=row.get("story_id"),
        spread_number=row.get("spread_number"),
        prompt=row["prompt"],
        image_base64=image_base64,
        character_ref_base64=ref_base64,
        check_text_free=bool(row.get("check_text_free", 1)),
        check_characters=bool(row.get("check_characters", 1)),
        check_composition=bool(row.get("check_composition", 1)),
        vlm_model=row.get("vlm_model", "unknown"),
        vlm_raw_response=row.get("vlm_raw_response"),
        vlm_overall_pass=bool(row.get("vlm_overall_pass", 1)),
        vlm_text_free=bool(row["vlm_text_free"]) if row.get("vlm_text_free") is not None else None,
        vlm_character_match_score=row.get("vlm_character_match_score"),
        vlm_scene_accuracy_score=row.get("vlm_scene_accuracy_score"),
        vlm_composition_score=row.get("vlm_composition_score"),
        vlm_style_score=row.get("vlm_style_score"),
        vlm_issues=issues,
        human_verdict=bool(row["human_verdict"]) if row.get("human_verdict") is not None else None,
        human_notes=row.get("human_notes"),
        annotated_at=row.get("annotated_at"),
        created_at=row["created_at"],
    )


@router.get(
    "/vlm-evals",
    response_model=list[EvalSummary],
    summary="List VLM evaluations",
    description="Get a paginated list of VLM evaluations for annotation.",
)
async def list_evaluations(
    unannotated_only: bool = Query(default=False, description="Only show unannotated evaluations"),
    story_id: Optional[str] = Query(default=None, description="Filter by story ID"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number to return"),
    offset: int = Query(default=0, ge=0, description="Number to skip"),
):
    """List VLM evaluations."""
    rows = await VLMEvalRepository.list_evaluations(
        unannotated_only=unannotated_only,
        story_id=story_id,
        limit=limit,
        offset=offset,
    )
    return [_row_to_summary(row) for row in rows]


@router.get(
    "/vlm-evals/stats",
    response_model=StatsResponse,
    summary="Get annotation statistics",
    description="Get statistics on annotation progress and VLM/human agreement.",
)
async def get_stats():
    """Get annotation statistics."""
    stats = await VLMEvalRepository.get_stats()
    return StatsResponse(**stats)


@router.get(
    "/vlm-evals/export",
    summary="Export annotated evaluations for GEPA",
    description="Export all annotated evaluations as JSON for GEPA optimization.",
)
async def export_for_gepa():
    """Export annotated evaluations for GEPA optimization."""
    rows = await VLMEvalRepository.export_for_gepa()

    # Convert to training-friendly format
    training_data = []
    for row in rows:
        training_data.append({
            "id": row["id"],
            "prompt": row["prompt"],
            "image_path": row.get("image_path"),
            "character_ref_paths": json.loads(row.get("character_ref_paths") or "[]"),
            "vlm_prediction": bool(row.get("vlm_overall_pass", 1)),
            "human_label": bool(row.get("human_verdict", 1)),
            "is_correct": row.get("vlm_overall_pass") == row.get("human_verdict"),
            "vlm_raw_response": row.get("vlm_raw_response"),
            "human_notes": row.get("human_notes"),
        })

    return JSONResponse(content={
        "count": len(training_data),
        "evaluations": training_data,
    })


@router.get(
    "/vlm-evals/{eval_id}",
    response_model=EvalDetail,
    summary="Get evaluation detail",
    description="Get full details of an evaluation including images as base64.",
)
async def get_evaluation(eval_id: str):
    """Get a single evaluation with full detail."""
    row = await VLMEvalRepository.get_evaluation(eval_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Evaluation {eval_id} not found")

    return _row_to_detail(row)


@router.post(
    "/vlm-evals/{eval_id}/annotate",
    summary="Annotate an evaluation",
    description="Add human ground truth annotation to an evaluation.",
)
async def annotate_evaluation(eval_id: str, request: AnnotateRequest):
    """Add human annotation to an evaluation."""
    success = await VLMEvalRepository.annotate(
        eval_id=eval_id,
        human_verdict=request.human_verdict,
        human_notes=request.human_notes,
    )

    if not success:
        raise HTTPException(status_code=404, detail=f"Evaluation {eval_id} not found")

    return {"status": "annotated", "eval_id": eval_id}
