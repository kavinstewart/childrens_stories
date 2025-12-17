"""
Image generation configuration for the Children's Story Generator.

Uses Nano Banana Pro (Gemini 3 Pro Image) for illustration generation.
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig, Modality

# Load environment variables from .env file
load_dotenv()

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


def extract_image_from_response(response) -> bytes:
    """
    Extract image bytes from a Gemini API response.

    Args:
        response: The response from genai.Client.models.generate_content()

    Returns:
        Image bytes (PNG/JPEG)

    Raises:
        ValueError: If no image found in response
    """
    import base64

    for part in response.candidates[0].content.parts:
        if hasattr(part, 'inline_data') and part.inline_data:
            data = part.inline_data.data
            return base64.b64decode(data) if isinstance(data, str) else data

    raise ValueError("No image found in response")
