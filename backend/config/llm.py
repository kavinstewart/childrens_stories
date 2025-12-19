"""
LLM configuration for the Children's Story Generator.

Uses dual-LM architecture:
- inference_lm: Fast/cheap model for generation (high volume)
- reflection_lm: Strong model for GEPA analysis (low volume)
"""

import os
from dotenv import load_dotenv
import dspy

# Load environment variables from .env file
load_dotenv()


def get_inference_lm() -> dspy.LM:
    """
    Get the inference LM for story generation.

    Priority order:
    1. Gemini 3 Pro (GOOGLE_API_KEY) - Best for creative writing
    2. Claude Opus 4.5 (ANTHROPIC_API_KEY)
    3. GPT 5.2 (OPENAI_API_KEY)
    """
    if os.getenv("GOOGLE_API_KEY"):
        return dspy.LM(
            "gemini/gemini-3-pro-preview",
            api_key=os.getenv("GOOGLE_API_KEY"),
            max_tokens=4096,
            temperature=1.0,  # Google recommends 1.0 for Gemini 3 (optimized for it)
        )
    elif os.getenv("ANTHROPIC_API_KEY"):
        return dspy.LM(
            "anthropic/claude-opus-4-5-20251101",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=4096,
            temperature=1.0,  # Anthropic recommends 1.0 for creative writing
        )
    elif os.getenv("OPENAI_API_KEY"):
        return dspy.LM(
            "gpt-5.2",
            api_key=os.getenv("OPENAI_API_KEY"),
            max_tokens=16000,  # GPT-5 reasoning models require >= 16000
            temperature=1.0,   # GPT-5 reasoning models require 1.0
        )
    else:
        raise ValueError(
            "No API key found. Set GOOGLE_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY in .env"
        )


def get_reflection_lm() -> dspy.LM:
    """
    Get the reflection LM for GEPA optimization.
    Uses a stronger model for analyzing errors and improving prompts.
    """
    if os.getenv("GOOGLE_API_KEY"):
        return dspy.LM(
            "gemini/gemini-3-pro-preview",
            api_key=os.getenv("GOOGLE_API_KEY"),
            max_tokens=8192,
            temperature=1.0,
        )
    elif os.getenv("ANTHROPIC_API_KEY"):
        return dspy.LM(
            "anthropic/claude-sonnet-4-20250514",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=8192,
            temperature=1.0,
        )
    elif os.getenv("OPENAI_API_KEY"):
        return dspy.LM(
            "gpt-5.2",
            api_key=os.getenv("OPENAI_API_KEY"),
            max_tokens=16000,  # GPT-5 reasoning models require >= 16000
            temperature=1.0,
        )
    else:
        raise ValueError(
            "No API key found. Set GOOGLE_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY in .env"
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
