"""Progress tracker for story generation."""

import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional

import asyncpg

from ..config import get_dsn

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

    Uses async PostgreSQL writes. Includes debouncing to limit DB writes.
    """

    def __init__(
        self,
        story_id: str,
        min_update_interval: float = 0.5,
    ):
        self.story_id = story_id
        self.min_update_interval = min_update_interval

        self.last_update_time: Optional[float] = None
        self.last_stage: Optional[str] = None
        self.warnings: list[str] = []

        # Create a dedicated pool for progress updates
        # This avoids issues with sharing connections across threads
        self._pool: Optional[asyncpg.Pool] = None
        self._dsn = get_dsn()

    async def update_async(
        self,
        stage: str,
        detail: str,
        completed: Optional[int] = None,
        total: Optional[int] = None,
        **kwargs,
    ) -> None:
        """
        Update progress asynchronously.

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

        # Write to DB asynchronously
        await self._write_progress_async(stage, detail, percentage, counters)

        # Update tracking state
        self.last_update_time = now
        self.last_stage = stage

    def update(
        self,
        stage: str,
        detail: str,
        completed: Optional[int] = None,
        total: Optional[int] = None,
        **kwargs,
    ) -> None:
        """
        Update progress synchronously (for use in sync code paths).

        This runs the async update in a new event loop iteration.
        For background thread usage, prefer using update_async directly.
        """
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, schedule the update
            asyncio.create_task(
                self.update_async(stage, detail, completed, total, **kwargs)
            )
        except RuntimeError:
            # No running loop - create one for this call
            asyncio.run(
                self.update_async(stage, detail, completed, total, **kwargs)
            )

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

    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create the connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=1)
        return self._pool

    async def _write_progress_async(
        self,
        stage: str,
        detail: str,
        percentage: int,
        counters: dict,
    ) -> None:
        """Write progress to database asynchronously."""
        progress_data = {
            "stage": stage,
            "stage_detail": detail,
            "percentage": percentage,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **counters,
        }

        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE stories SET progress_json = $1 WHERE id = $2",
                    json.dumps(progress_data),
                    self.story_id,
                )
        except Exception as e:
            # Log full exception for debugging - progress failures indicate DB issues
            logger.error(f"Failed to update progress for {self.story_id}: {e}", exc_info=True)

    async def close(self) -> None:
        """Close the dedicated pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
