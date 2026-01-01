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


class RegenerateSpreadRequest(BaseModel):
    """Request body for regenerating a spread illustration."""

    prompt: str | None = Field(
        default=None,
        max_length=4000,  # Prevent excessively long prompts that could exceed model limits
        description="Optional custom prompt to use instead of the default composed prompt. "
                    "If not provided, uses the original illustration_prompt with style template.",
    )
