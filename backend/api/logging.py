"""Structured logging infrastructure for the API layer.

Provides JSON-formatted logging for production and human-readable
logging for development, plus a StoryLogger helper for story generation events.
"""

import json
import logging
import sys
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "story_id"):
            log_data["story_id"] = record.story_id
        if hasattr(record, "stage"):
            log_data["stage"] = record.stage
        if hasattr(record, "duration"):
            log_data["duration"] = record.duration
        if hasattr(record, "attempt"):
            log_data["attempt"] = record.attempt
        if hasattr(record, "error_type"):
            log_data["error_type"] = record.error_type

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def configure_logging(json_format: bool = True, level: int = logging.INFO) -> None:
    """Configure structured logging for the application."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    root_logger.addHandler(handler)


class StoryLogger:
    """Logger for story generation events with structured fields."""

    def __init__(self):
        self.logger = logging.getLogger("story_generation")

    def generation_started(self, story_id: str, generation_type: str) -> None:
        self.logger.info(
            "Story generation started",
            extra={"story_id": story_id, "stage": "started", "generation_type": generation_type},
        )

    def stage_completed(self, story_id: str, stage: str, duration: float = None) -> None:
        extra = {"story_id": story_id, "stage": stage}
        if duration:
            extra["duration"] = round(duration, 2)
        self.logger.info(f"Stage completed: {stage}", extra=extra)

    def generation_completed(self, story_id: str, duration: float) -> None:
        self.logger.info(
            "Story generation completed",
            extra={"story_id": story_id, "stage": "completed", "duration": round(duration, 2)},
        )

    def generation_failed(self, story_id: str, error: Exception, stage: str = None) -> None:
        extra = {"story_id": story_id, "stage": "failed", "error_type": type(error).__name__}
        if stage:
            extra["failed_at_stage"] = stage
        self.logger.error(f"Story generation failed: {error}", extra=extra, exc_info=True)

    def retry_attempt(self, story_id: str, attempt: int, reason: str) -> None:
        self.logger.warning(
            f"Retry attempt {attempt}: {reason}",
            extra={"story_id": story_id, "attempt": attempt},
        )


# Global story logger instance
story_logger = StoryLogger()
