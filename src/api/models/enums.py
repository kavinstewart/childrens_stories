"""Shared enums for API models."""

from enum import Enum


class GenerationType(str, Enum):
    """Type of story generation to perform."""

    SIMPLE = "simple"
    STANDARD = "standard"
    ILLUSTRATED = "illustrated"


class JobStatus(str, Enum):
    """Status of a story generation job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
