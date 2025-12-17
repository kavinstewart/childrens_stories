"""Pydantic models for API requests."""

from pydantic import BaseModel, Field

from .enums import GenerationType


class CreateStoryRequest(BaseModel):
    """Request body for creating a new story."""

    goal: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Learning goal or theme for the story",
        examples=["teach kids that feedback is a gift", "explain friendship to children"],
    )
    target_age_range: str = Field(
        default="4-7",
        pattern=r"^\d+-\d+$",
        description="Target age range in format 'min-max'",
    )
    generation_type: GenerationType = Field(
        default=GenerationType.STANDARD,
        description="Type of generation: simple (fast, single attempt), standard (quality loop), illustrated (with images)",
    )
    quality_threshold: int = Field(
        default=7,
        ge=1,
        le=10,
        description="Minimum quality score (1-10) to accept story",
    )
    max_attempts: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum generation attempts if quality threshold not met",
    )
