"""Progress tracker for story generation."""

import asyncio
import time
import logging
from datetime import datetime
from typing import Optional

from ..database.repository import StoryRepository

logger = logging.getLogger(__name__)

# Stage weight mapping for percentage calculation
STAGE_WEIGHTS = {
    "outline": (0, 15),
    "spreads": (15, 25),
    "quality": (25, 30),
    "character_refs": (30, 40),
    "illustrations": (40, 100),
}


class ProgressTracker:
    """
    Tracks and persists story generation progress.

    Provides a synchronous interface that schedules async DB writes
    via an event loop. Includes debouncing to limit DB writes.
    """

    def __init__(
        self,
        story_id: str,
        repo: StoryRepository,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        min_update_interval: float = 0.5,
    ):
        self.story_id = story_id
        self.repo = repo
        self.loop = loop
        self.min_update_interval = min_update_interval

        self.last_update_time: Optional[float] = None
        self.last_stage: Optional[str] = None
        self.warnings: list[str] = []

    def update(
        self,
        stage: str,
        detail: str,
        completed: Optional[int] = None,
        total: Optional[int] = None,
        **kwargs,
    ) -> None:
        """
        Update progress synchronously.

        Args:
            stage: Current pipeline stage
            detail: Human-readable message
            completed: Items completed in current stage (for granular progress)
            total: Total items in current stage
            **kwargs: Additional fields (quality_attempt, quality_score, etc.)
        """
        now = time.time()

        # Determine if we should skip this update (debouncing)
        is_stage_change = stage != self.last_stage
        is_completion = completed is not None and total is not None and completed == total

        if not is_stage_change and not is_completion and self.last_update_time:
            if now - self.last_update_time < self.min_update_interval:
                return  # Skip - too soon after last update

        # Calculate percentage
        percentage = self._calculate_percentage(stage, completed, total)

        # Build counters
        counters = {}
        if completed is not None:
            if stage == "character_refs":
                counters["characters_completed"] = completed
                counters["characters_total"] = total
            elif stage == "illustrations":
                counters["spreads_completed"] = completed
                counters["spreads_total"] = total

        # Add any additional fields
        counters.update(kwargs)

        # Add accumulated warnings
        if self.warnings:
            counters["warnings"] = self.warnings.copy()

        # Schedule async DB write
        self._schedule_update(stage, detail, percentage, counters)

        # Update tracking state
        self.last_update_time = now
        self.last_stage = stage

    def add_warning(self, warning: str) -> None:
        """Add a non-fatal warning."""
        self.warnings.append(warning)

    def _calculate_percentage(
        self,
        stage: str,
        completed: Optional[int],
        total: Optional[int],
    ) -> int:
        """Calculate weighted percentage based on stage and progress."""
        if stage not in STAGE_WEIGHTS:
            return 0

        start_pct, end_pct = STAGE_WEIGHTS[stage]

        # If we have granular counters, interpolate within stage
        if completed is not None and total is not None and total > 0:
            progress = completed / total
            return int(start_pct + (end_pct - start_pct) * progress)

        # Otherwise, just use stage start
        return start_pct

    def _schedule_update(
        self,
        stage: str,
        detail: str,
        percentage: int,
        counters: dict,
    ) -> None:
        """Schedule async DB write."""
        if self.loop is None:
            logger.debug(f"No event loop, skipping progress update for {self.story_id}")
            return

        try:
            asyncio.run_coroutine_threadsafe(
                self.repo.update_progress(
                    story_id=self.story_id,
                    stage=stage,
                    stage_detail=detail,
                    percentage=percentage,
                    **counters,
                ),
                self.loop,
            )
        except Exception as e:
            # Silent fail - progress updates are non-critical
            logger.warning(f"Failed to update progress for {self.story_id}: {e}")
