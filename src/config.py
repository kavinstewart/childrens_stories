"""
DSPy configuration for the Children's Story Generator.

Uses dual-LM architecture:
- inference_lm: Fast/cheap model for generation (high volume)
- reflection_lm: Strong model for GEPA analysis (low volume)
- image_client: Nano Banana Pro for illustration generation
"""

import os
from dotenv import load_dotenv
import dspy
from google import genai
from google.genai.types import GenerateContentConfig, Modality

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
    elif os.getenv("ANTHROPIC_API_KEY"):
        return dspy.LM(
            "anthropic/claude-sonnet-4-20250514",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=4096,
            temperature=0.7,
        )
    else:
        raise ValueError(
            "No API key found. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or OPENROUTER_API_KEY in .env"
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
    Configure DSPy with the appropriate LM.

    Args:
        use_reflection_lm: If True, use the reflection LM (for GEPA).
                          If False, use the inference LM (default).
    """
    if use_reflection_lm:
        lm = get_reflection_lm()
    else:
        lm = get_inference_lm()

    dspy.configure(lm=lm)


# Story generation constants
STORY_CONSTANTS = {
    "target_page_count": 16,  # Can be 16, 24, or 32
    "target_word_count": 500,  # Sweet spot for picture books
    "words_per_page_min": 20,
    "words_per_page_max": 50,
    "max_word_count": 1000,  # Industry standard limit
}

# Image generation constants
IMAGE_CONSTANTS = {
    "model": "gemini-3-pro-image-preview",  # Nano Banana Pro
    "max_reference_images": 14,  # Nano Banana Pro supports up to 14
    "max_faces": 5,  # 5-face memory system
}


def get_image_client() -> genai.Client:
    """
    Get the Nano Banana Pro (Gemini 3 Pro Image) client for illustration generation.

    Uses GOOGLE_API_KEY from environment.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment. Set it in .env file.")

    return genai.Client(api_key=api_key)


def get_image_model() -> str:
    """Get the image model ID."""
    return IMAGE_CONSTANTS["model"]


def get_image_config() -> GenerateContentConfig:
    """Get the default config for image generation."""
    return GenerateContentConfig(
        response_modalities=[Modality.TEXT, Modality.IMAGE]
    )
