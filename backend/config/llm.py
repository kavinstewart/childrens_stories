"""
LLM configuration for the Children's Story Generator.

Uses dual-LM architecture:
- inference_lm: Fast/cheap model for generation (high volume)
- reflection_lm: Strong model for GEPA analysis (low volume)

Includes:
- 120s timeout per LLM call to fail fast on hanging connections
- Retry with exponential backoff for transient network errors
"""

import os
import logging
from dotenv import load_dotenv
import dspy
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

# Load environment variables from .env file
load_dotenv()

# Logging for retry attempts
logger = logging.getLogger(__name__)

# Timeout for LLM calls (seconds)
LLM_TIMEOUT = 120

# Network errors that should trigger retry
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    BrokenPipeError,
    OSError,  # Catches [Errno 32] Broken pipe
)


def get_inference_lm() -> dspy.LM:
    """
    Get the inference LM for story generation.

    Priority order:
    1. Gemini 3 Pro (GOOGLE_API_KEY) - Best for creative writing
    2. Claude Opus 4.5 (ANTHROPIC_API_KEY)
    3. GPT 5.2 (OPENAI_API_KEY)

    Includes 120s timeout per call.
    """
    if os.getenv("GOOGLE_API_KEY"):
        return dspy.LM(
            "gemini/gemini-3-pro-preview",
            api_key=os.getenv("GOOGLE_API_KEY"),
            max_tokens=4096,
            temperature=1.0,  # Google recommends 1.0 for Gemini 3 (optimized for it)
            timeout=LLM_TIMEOUT,
        )
    elif os.getenv("ANTHROPIC_API_KEY"):
        return dspy.LM(
            "anthropic/claude-opus-4-5-20251101",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=4096,
            temperature=1.0,  # Anthropic recommends 1.0 for creative writing
            timeout=LLM_TIMEOUT,
        )
    elif os.getenv("OPENAI_API_KEY"):
        return dspy.LM(
            "gpt-5.2",
            api_key=os.getenv("OPENAI_API_KEY"),
            max_tokens=16000,  # GPT-5 reasoning models require >= 16000
            temperature=1.0,   # GPT-5 reasoning models require 1.0
            timeout=LLM_TIMEOUT,
        )
    else:
        raise ValueError(
            "No API key found. Set GOOGLE_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY in .env"
        )


def get_reflection_lm() -> dspy.LM:
    """
    Get the reflection LM for GEPA optimization.
    Uses a stronger model for analyzing errors and improving prompts.
    Includes 120s timeout per call.
    """
    if os.getenv("GOOGLE_API_KEY"):
        return dspy.LM(
            "gemini/gemini-3-pro-preview",
            api_key=os.getenv("GOOGLE_API_KEY"),
            max_tokens=8192,
            temperature=1.0,
            timeout=LLM_TIMEOUT,
        )
    elif os.getenv("ANTHROPIC_API_KEY"):
        return dspy.LM(
            "anthropic/claude-sonnet-4-20250514",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=8192,
            temperature=1.0,
            timeout=LLM_TIMEOUT,
        )
    elif os.getenv("OPENAI_API_KEY"):
        return dspy.LM(
            "gpt-5.2",
            api_key=os.getenv("OPENAI_API_KEY"),
            max_tokens=16000,  # GPT-5 reasoning models require >= 16000
            temperature=1.0,
            timeout=LLM_TIMEOUT,
        )
    else:
        raise ValueError(
            "No API key found. Set GOOGLE_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY in .env"
        )


# Retry decorator for LLM calls with network errors
llm_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


def get_inference_model_name() -> str:
    """Get the name of the inference model that will be used."""
    if os.getenv("GOOGLE_API_KEY"):
        return "gemini-3-pro-preview"
    elif os.getenv("ANTHROPIC_API_KEY"):
        return "claude-opus-4-5-20251101"
    elif os.getenv("OPENAI_API_KEY"):
        return "gpt-5.2"
    else:
        return "unknown"


def configure_dspy(use_reflection_lm: bool = False) -> None:
    """
    Configure DSPy with the appropriate LM globally.

    Args:
        use_reflection_lm: If True, use the reflection LM (for GEPA).
                          If False, use the inference LM (default).

    Note:
        For testing or when you need explicit control, prefer passing
        an LM directly to StoryGenerator(lm=...) instead of using
        this global configuration.
    """
    if use_reflection_lm:
        lm = get_reflection_lm()
    else:
        lm = get_inference_lm()

    dspy.configure(lm=lm)
