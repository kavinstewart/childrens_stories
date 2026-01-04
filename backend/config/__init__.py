"""
Configuration module for the Children's Story Generator.

Re-exports all configuration for backwards compatibility.
"""

from .llm import configure_dspy, get_inference_lm, get_reflection_lm, get_inference_model_name, llm_retry, LLM_TIMEOUT
from .image import (
    IMAGE_CONSTANTS,
    get_image_client,
    get_image_model,
    get_image_config,
    extract_image_from_response,
    image_retry,
)

__all__ = [
    # LLM
    "configure_dspy",
    "get_inference_lm",
    "get_reflection_lm",
    "get_inference_model_name",
    "llm_retry",
    "LLM_TIMEOUT",
    # Image
    "IMAGE_CONSTANTS",
    "get_image_client",
    "get_image_model",
    "get_image_config",
    "extract_image_from_response",
    "image_retry",
]
