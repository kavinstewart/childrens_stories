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

    Uses Claude Opus 4.5 for high-quality creative writing.
    Ranked #1 in blind comparison for children's story generation.
    """
    if os.getenv("ANTHROPIC_API_KEY"):
        return dspy.LM(
            "anthropic/claude-opus-4-5-20251101",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=4096,
            temperature=0.7,
        )
    elif os.getenv("CEREBRAS_API_KEY"):
        # Fallback to Cerebras Qwen3-235B
        return dspy.LM(
            "cerebras/qwen-3-235b-a22b-instruct-2507",
            api_key=os.getenv("CEREBRAS_API_KEY"),
            max_tokens=4096,
            temperature=0.6,
        )
    elif os.getenv("OPENROUTER_API_KEY"):
        # Fallback to OpenRouter if no Cerebras key
        return dspy.LM(
            "openrouter/qwen/qwen3-235b-a22b",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            api_base="https://openrouter.ai/api/v1",
            max_tokens=4096,
            temperature=0.6,
        )
    elif os.getenv("OPENAI_API_KEY"):
        return dspy.LM(
            "openai/gpt-4o",
            api_key=os.getenv("OPENAI_API_KEY"),
            max_tokens=4096,
            temperature=0.7,
        )
    else:
        raise ValueError(
            "No API key found. Set ANTHROPIC_API_KEY, CEREBRAS_API_KEY, OPENROUTER_API_KEY, or OPENAI_API_KEY in .env"
        )


def get_reflection_lm() -> dspy.LM:
    """
    Get the reflection LM for GEPA optimization.
    Uses a stronger model for analyzing errors and improving prompts.
    """
    if os.getenv("OPENROUTER_API_KEY"):
        return dspy.LM(
            "openrouter/openai/gpt-4.1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            api_base="https://openrouter.ai/api/v1",
            max_tokens=8192,
            temperature=1.0,
        )
    elif os.getenv("OPENAI_API_KEY"):
        return dspy.LM(
            "openai/gpt-4o",
            api_key=os.getenv("OPENAI_API_KEY"),
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
    else:
        raise ValueError(
            "No API key found. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or OPENROUTER_API_KEY in .env"
        )


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
