"""Pydantic models for API responses."""

from pydantic import BaseModel, Field, computed_field
from typing import Optional
from datetime import datetime

from .enums import GenerationType, JobStatus


class StorySpreadResponse(BaseModel):
    """A single spread (two facing pages) of the story.

    A picture book has 12 spreads for story content.
    Each spread has 25-40 words and one illustration.
    """

    spread_number: int
    text: str
    word_count: int
    was_revised: bool = False
    page_turn_note: Optional[str] = None  # What makes reader want to turn
    illustration_prompt: Optional[str] = None
    illustration_url: Optional[str] = None


# Backwards compatibility alias
StoryPageResponse = StorySpreadResponse


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


class StoryOutlineResponse(BaseModel):
    """Story outline metadata."""

    title: str
    protagonist_goal: str
    stakes: str
    characters: str
    setting: str
    emotional_arc: str
    plot_summary: str
    moral: str
    spread_count: int  # Number of spreads (typically 12)


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

    id: str
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

    # Backwards compatibility aliases
    @computed_field
    @property
    def page_count(self) -> Optional[int]:
        """Alias for spread_count (backwards compatibility)."""
        return self.spread_count

    @computed_field
    @property
    def pages(self) -> Optional[list[StorySpreadResponse]]:
        """Alias for spreads (backwards compatibility)."""
        return self.spreads


class StoryListResponse(BaseModel):
    """Paginated list of stories."""

    stories: list[StoryResponse]
    total: int
    limit: int
    offset: int


class CreateStoryResponse(BaseModel):
    """Response when creating a new story job."""

    id: str
    status: JobStatus
    message: str = Field(
        default="Story generation started. Poll GET /stories/{id} for status."
    )
