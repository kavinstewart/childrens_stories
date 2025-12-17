"""
Configuration module for the Children's Story Generator.

Re-exports all configuration for backwards compatibility.
"""

from .llm import configure_dspy, get_inference_lm, get_reflection_lm
from .story import STORY_CONSTANTS
from .image import (
    IMAGE_CONSTANTS,
    get_image_client,
    get_image_model,
    get_image_config,
    extract_image_from_response,
)

__all__ = [
    # LLM
    "configure_dspy",
    "get_inference_lm",
    "get_reflection_lm",
    # Story
    "STORY_CONSTANTS",
    # Image
    "IMAGE_CONSTANTS",
    "get_image_client",
    "get_image_model",
    "get_image_config",
    "extract_image_from_response",
]
