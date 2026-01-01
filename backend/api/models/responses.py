"""Pydantic models for API responses."""

from uuid import UUID
from pydantic import BaseModel, Field, computed_field
from typing import Optional
from datetime import datetime

from .enums import GenerationType, JobStatus


class StorySpreadResponse(BaseModel):
    """A single spread (two facing pages) of the story.

    A picture book has 12 spreads for story content.
    Each spread has 35-50 words and one illustration.
    """

    spread_number: int
    text: str
    word_count: int
    was_revised: bool = False
    page_turn_note: Optional[str] = None  # What makes reader want to turn
    illustration_prompt: Optional[str] = None
    illustration_url: Optional[str] = None
    illustration_updated_at: Optional[datetime] = None  # For cache busting after regeneration


class QualityJudgmentResponse(BaseModel):
    """Quality assessment of the story."""

    overall_score: int
    verdict: str
    engagement_score: int
    read_aloud_score: int
    emotional_truth_score: int
    coherence_score: int
    chekhov_score: int
    has_critical_failures: bool
    specific_problems: str


class IllustrationStyleResponse(BaseModel):
    """Illustration style definition for consistency."""

    name: str
    description: str
    prompt_prefix: str
    best_for: list[str] = []
    lighting_direction: str = ""


class StoryOutlineResponse(BaseModel):
    """Story outline metadata."""

    title: str
    characters: str = ""
    setting: str = ""
    plot_summary: str = ""
    spread_count: int = 12  # Number of spreads (typically 12)
    illustration_style: Optional[IllustrationStyleResponse] = None  # For regeneration consistency


class CharacterReferenceResponse(BaseModel):
    """Character reference image info."""

    character_name: str
    character_description: Optional[str] = None
    reference_image_url: Optional[str] = None


class StoryProgressResponse(BaseModel):
    """Progress tracking for story generation."""

    stage: str  # outline, spreads, quality, character_refs, illustrations, failed
    stage_detail: str  # Human-readable message
    percentage: int  # 0-100, weighted by stage

    # Granular counters (populated when relevant)
    characters_total: Optional[int] = None
    characters_completed: Optional[int] = None
    spreads_total: Optional[int] = None
    spreads_completed: Optional[int] = None
    quality_attempt: Optional[int] = None
    quality_attempts_max: Optional[int] = None
    quality_score: Optional[int] = None

    # Error context
    warnings: list[str] = Field(default_factory=list)

    updated_at: Optional[datetime] = None


class StoryResponse(BaseModel):
    """Full story response with all data."""

    id: UUID
    status: JobStatus
    goal: str
    target_age_range: str
    generation_type: GenerationType
    llm_model: Optional[str] = None  # Model used for generation
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Populated when completed
    title: Optional[str] = None
    word_count: Optional[int] = None
    spread_count: Optional[int] = None  # Number of spreads (typically 12)
    attempts: Optional[int] = None

    outline: Optional[StoryOutlineResponse] = None
    spreads: Optional[list[StorySpreadResponse]] = None
    judgment: Optional[QualityJudgmentResponse] = None
    character_references: Optional[list[CharacterReferenceResponse]] = None

    # Progress tracking (populated while running)
    progress: Optional[StoryProgressResponse] = None

    # Error info
    error_message: Optional[str] = None

    @computed_field
    @property
    def is_illustrated(self) -> bool:
        """Derived from generation_type - True when generation_type is ILLUSTRATED."""
        return self.generation_type == GenerationType.ILLUSTRATED


class StoryListResponse(BaseModel):
    """Paginated list of stories."""

    stories: list[StoryResponse]
    total: int
    limit: int
    offset: int


class CreateStoryResponse(BaseModel):
    """Response when creating a new story job."""

    id: UUID
    status: JobStatus
    message: str = Field(
        default="Story generation started. Poll GET /stories/{id} for status."
    )


class StoryRecommendationItem(BaseModel):
    """A single story recommendation (lightweight)."""

    id: UUID
    title: Optional[str] = None
    goal: str
    cover_url: Optional[str] = None
    is_illustrated: bool = False


class StoryRecommendationsResponse(BaseModel):
    """Response for story recommendations."""

    recommendations: list[StoryRecommendationItem]


class RegenerateSpreadResponse(BaseModel):
    """Response when starting a spread regeneration job."""

    job_id: str
    story_id: str
    spread_number: int
    status: JobStatus
    message: str = Field(
        default="Spread regeneration started. Poll GET /stories/{story_id} for updated illustration."
    )
