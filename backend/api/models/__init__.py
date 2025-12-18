"""Pydantic models for API requests and responses."""

from .requests import CreateStoryRequest
from .responses import (
    StoryResponse,
    StoryListResponse,
    CreateStoryResponse,
    StorySpreadResponse,
    StoryPageResponse,  # Backwards compatibility alias
    StoryOutlineResponse,
    QualityJudgmentResponse,
    CharacterReferenceResponse,
    JobStatus,
    GenerationType,
)

__all__ = [
    "CreateStoryRequest",
    "StoryResponse",
    "StoryListResponse",
    "CreateStoryResponse",
    "StorySpreadResponse",
    "StoryPageResponse",  # Backwards compatibility alias
    "StoryOutlineResponse",
    "QualityJudgmentResponse",
    "CharacterReferenceResponse",
    "JobStatus",
    "GenerationType",
]
