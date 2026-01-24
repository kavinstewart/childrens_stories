"""
Cost tracking for story generation.

Uses contextvars for invisible tracking without parameter threading.
This module provides the data collection layer - see cost_calculator.py
for computing costs from usage data.
"""

import threading
from contextvars import ContextVar
from dataclasses import dataclass, field
from types import TracebackType
from typing import Optional

from backend.core.cost_calculator import calculate_cost


@dataclass
class UsageData:
    """Tracks resource usage for a single generation job.

    Thread-safe: uses internal lock for concurrent mutations when shared
    across ThreadPoolExecutor workers via copy_context().
    """

    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    llm_model: str = ""
    llm_calls: int = 0
    image_count: int = 0
    image_model: str = ""
    image_retries: int = 0
    llm_total_duration_ms: int = 0
    llm_durations_ms: list[int] = field(default_factory=list)

    # Lock for thread-safe mutations (excluded from repr/compare/serialization)
    _lock: threading.Lock = field(
        default_factory=threading.Lock, repr=False, compare=False
    )

    def add_image(self, model: str, was_retry: bool = False) -> None:
        """Thread-safe image count increment."""
        with self._lock:
            self.image_count += 1
            self.image_model = model
            if was_retry:
                self.image_retries += 1

    def to_dict(self) -> dict:
        """Serialize to dict for JSON storage. Excludes _lock."""
        return {
            "llm_input_tokens": self.llm_input_tokens,
            "llm_output_tokens": self.llm_output_tokens,
            "llm_model": self.llm_model,
            "llm_calls": self.llm_calls,
            "image_count": self.image_count,
            "image_model": self.image_model,
            "image_retries": self.image_retries,
            "llm_total_duration_ms": self.llm_total_duration_ms,
            "llm_durations_ms": self.llm_durations_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UsageData":
        """Create from dict (e.g., from JSON storage). Lock created automatically."""
        return cls(
            llm_input_tokens=data.get("llm_input_tokens", 0),
            llm_output_tokens=data.get("llm_output_tokens", 0),
            llm_model=data.get("llm_model", ""),
            llm_calls=data.get("llm_calls", 0),
            image_count=data.get("image_count", 0),
            image_model=data.get("image_model", ""),
            image_retries=data.get("image_retries", 0),
            llm_total_duration_ms=data.get("llm_total_duration_ms", 0),
            llm_durations_ms=data.get("llm_durations_ms", []),
        )


# Context variable for tracking - each thread/task gets its own context
_usage: ContextVar[Optional[UsageData]] = ContextVar("usage", default=None)


def start_tracking() -> UsageData:
    """
    Start tracking usage for the current context.

    Call this at the beginning of a generation job. Returns the UsageData
    instance that will accumulate usage during the job.
    """
    usage = UsageData()
    _usage.set(usage)
    return usage


def get_current_usage() -> Optional[UsageData]:
    """
    Get the current usage data, or None if tracking not started.

    Use this to retrieve accumulated usage at the end of a job.
    """
    return _usage.get()


def clear_tracking() -> None:
    """
    Clear the current tracking context.

    Call this at the end of a job or in cleanup code.
    """
    _usage.set(None)


def record_llm_usage(input_tokens: int, output_tokens: int, model: str) -> None:
    """
    Record LLM token usage for the current context.

    Args:
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens generated
        model: Model identifier (e.g., "gemini-3-pro-preview")

    No-op if tracking not started.
    """
    usage = _usage.get()
    if usage is None:
        return

    usage.llm_input_tokens += input_tokens
    usage.llm_output_tokens += output_tokens
    usage.llm_calls += 1
    usage.llm_model = model  # Last model used (typically same throughout)


def record_image_generation(model: str, was_retry: bool = False) -> None:
    """
    Record an image generation for the current context.

    Thread-safe: uses UsageData.add_image() for concurrent access.

    Args:
        model: Model identifier (e.g., "gemini-3-pro-image-preview")
        was_retry: True if this was a retry attempt

    No-op if tracking not started.
    """
    usage = _usage.get()
    if usage is None:
        return

    usage.add_image(model, was_retry)


# Context var to track last processed history index for each LM
_last_history_index: ContextVar[int] = ContextVar("last_history_index", default=0)


def record_llm_usage_from_history(lm) -> None:
    """
    Record LLM usage from DSPy LM history since last check.

    Call this after DSPy operations complete to capture token usage.
    Uses the LM's history attribute to extract usage data.

    Args:
        lm: A dspy.LM instance with history attribute

    No-op if tracking not started or LM has no history.
    """
    usage = _usage.get()
    if usage is None:
        return

    if not hasattr(lm, "history") or not lm.history:
        return

    # Get entries since last check
    last_idx = _last_history_index.get()
    new_entries = lm.history[last_idx:]

    for entry in new_entries:
        # Extract usage from response
        response = entry.get("response", {})
        usage_info = None

        # Handle different response structures
        if hasattr(response, "usage"):
            usage_info = response.usage
        elif isinstance(response, dict) and "usage" in response:
            usage_info = response["usage"]

        if usage_info:
            # LiteLLM/OpenAI style: prompt_tokens, completion_tokens
            input_tokens = getattr(usage_info, "prompt_tokens", None) or usage_info.get("prompt_tokens", 0)
            output_tokens = getattr(usage_info, "completion_tokens", None) or usage_info.get("completion_tokens", 0)

            # Gemini style: input_tokens, output_tokens
            if not input_tokens:
                input_tokens = getattr(usage_info, "input_tokens", None) or usage_info.get("input_tokens", 0)
            if not output_tokens:
                output_tokens = getattr(usage_info, "output_tokens", None) or usage_info.get("output_tokens", 0)

            usage.llm_input_tokens += input_tokens or 0
            usage.llm_output_tokens += output_tokens or 0
            usage.llm_calls += 1

        # Extract response duration from litellm's _response_ms attribute
        if hasattr(response, "_response_ms"):
            duration_ms = int(response._response_ms)
            usage.llm_total_duration_ms += duration_ms
            usage.llm_durations_ms.append(duration_ms)

    # Update model name from LM
    if hasattr(lm, "model"):
        # Strip provider prefix (e.g., "gemini/gemini-3-pro-preview" -> "gemini-3-pro-preview")
        model = lm.model
        usage.llm_model = model.split("/")[-1] if "/" in model else model

    # Update last processed index
    _last_history_index.set(len(lm.history))


def reset_history_tracking() -> None:
    """Reset the history tracking index (call when starting a new job)."""
    _last_history_index.set(0)


class CostTracker:
    """Context manager for cost tracking lifecycle.

    Handles start_tracking(), optional reset_history_tracking(), and
    clear_tracking() automatically. Captures usage data before cleanup.

    The usage_dict and cost_usd attributes are populated when the context
    exits, and can be accessed after the with block completes.

    Args:
        reset_history: If True, also calls reset_history_tracking() on entry.
                      Use this for jobs that use DSPy LM history tracking.

    Example:
        with CostTracker(reset_history=True) as costs:
            # ... do work that generates costs ...
        # After context exits:
        save_to_db(usage_json=costs.usage_dict, cost_usd=costs.cost_usd)
    """

    def __init__(self, reset_history: bool = False) -> None:
        self._reset_history = reset_history
        self.usage_dict: Optional[dict] = None
        self.cost_usd: Optional[float] = None

    def __enter__(self) -> "CostTracker":
        start_tracking()
        if self._reset_history:
            reset_history_tracking()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> bool:
        """Capture usage data and clear tracking."""
        usage = get_current_usage()
        if usage:
            self.usage_dict = usage.to_dict()
            self.cost_usd = float(calculate_cost(self.usage_dict))
        clear_tracking()
        return False  # Don't suppress exceptions
