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
from dataclasses import dataclass
from typing import Optional

from dotenv import find_dotenv, load_dotenv
import dspy
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

# Load environment variables from .env file (find_dotenv searches parent directories)
load_dotenv(find_dotenv())

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


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for a single LLM provider."""
    env_key: str
    inference_model: str
    reflection_model: str
    inference_max_tokens: int
    reflection_max_tokens: int


# Provider configurations in priority order
_PROVIDERS = [
    ProviderConfig(
        env_key="GOOGLE_API_KEY",
        inference_model="gemini/gemini-3-pro-preview",
        reflection_model="gemini/gemini-3-pro-preview",
        inference_max_tokens=4096,
        reflection_max_tokens=8192,
    ),
    ProviderConfig(
        env_key="ANTHROPIC_API_KEY",
        inference_model="anthropic/claude-opus-4-5-20251101",
        reflection_model="anthropic/claude-sonnet-4-20250514",
        inference_max_tokens=4096,
        reflection_max_tokens=8192,
    ),
    ProviderConfig(
        env_key="OPENAI_API_KEY",
        inference_model="gpt-5.2",
        reflection_model="gpt-5.2",
        inference_max_tokens=16000,  # GPT-5 reasoning models require >= 16000
        reflection_max_tokens=16000,
    ),
]


def _get_active_provider() -> tuple[ProviderConfig, str]:
    """
    Get the first available provider based on environment variables.

    Returns:
        Tuple of (provider config, api_key)

    Raises:
        ValueError: If no API key is found
    """
    for provider in _PROVIDERS:
        api_key = os.getenv(provider.env_key)
        if api_key:
            return provider, api_key

    env_keys = ", ".join(p.env_key for p in _PROVIDERS)
    raise ValueError(f"No API key found. Set one of: {env_keys} in .env")


def _get_active_provider_or_none() -> Optional[tuple[ProviderConfig, str]]:
    """Get active provider without raising, returns None if not found."""
    for provider in _PROVIDERS:
        api_key = os.getenv(provider.env_key)
        if api_key:
            return provider, api_key
    return None


def get_inference_lm() -> dspy.LM:
    """
    Get the inference LM for story generation.

    Priority order:
    1. Gemini 3 Pro (GOOGLE_API_KEY) - Best for creative writing
    2. Claude Opus 4.5 (ANTHROPIC_API_KEY)
    3. GPT 5.2 (OPENAI_API_KEY)

    Includes 120s timeout per call.
    """
    provider, api_key = _get_active_provider()
    return dspy.LM(
        provider.inference_model,
        api_key=api_key,
        max_tokens=provider.inference_max_tokens,
        temperature=1.0,
        timeout=LLM_TIMEOUT,
    )


def get_reflection_lm() -> dspy.LM:
    """
    Get the reflection LM for GEPA optimization.
    Uses a stronger model for analyzing errors and improving prompts.
    Includes 120s timeout per call.
    """
    provider, api_key = _get_active_provider()
    return dspy.LM(
        provider.reflection_model,
        api_key=api_key,
        max_tokens=provider.reflection_max_tokens,
        temperature=1.0,
        timeout=LLM_TIMEOUT,
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
    result = _get_active_provider_or_none()
    if result is None:
        return "unknown"
    provider, _ = result
    # Strip provider prefix (e.g., "gemini/" or "anthropic/") for display
    model = provider.inference_model
    return model.split("/")[-1] if "/" in model else model


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
