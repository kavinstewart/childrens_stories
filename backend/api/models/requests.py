"""Pydantic models for API requests."""

from pydantic import BaseModel, Field


class CreateStoryRequest(BaseModel):
    """Request body for creating a new story."""

    goal: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Learning goal or theme for the story",
        examples=["teach kids that feedback is a gift", "explain friendship to children"],
    )
