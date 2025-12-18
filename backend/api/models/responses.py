"""Pydantic models for API responses."""

from pydantic import BaseModel, Field, computed_field
from typing import Optional
from datetime import datetime

from .enums import GenerationType, JobStatus


class StoryPageResponse(BaseModel):
    """A single page of the story."""

    page_number: int
    text: str
    word_count: int
    was_revised: bool
    illustration_prompt: Optional[str] = None
    illustration_url: Optional[str] = None


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
    page_count: int


class CharacterReferenceResponse(BaseModel):
    """Character reference image info."""

    character_name: str
    character_description: Optional[str] = None
    reference_image_url: Optional[str] = None


class StoryResponse(BaseModel):
    """Full story response with all data."""

    id: str
    status: JobStatus
    goal: str
    target_age_range: str
    generation_type: GenerationType
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Populated when completed
    title: Optional[str] = None
    word_count: Optional[int] = None
    page_count: Optional[int] = None
    attempts: Optional[int] = None

    outline: Optional[StoryOutlineResponse] = None
    pages: Optional[list[StoryPageResponse]] = None
    judgment: Optional[QualityJudgmentResponse] = None
    character_references: Optional[list[CharacterReferenceResponse]] = None

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

    id: str
    status: JobStatus
    message: str = Field(
        default="Story generation started. Poll GET /stories/{id} for status."
    )
