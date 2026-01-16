"""
Pytest configuration for LLM evaluation tests.

Usage:
    poetry run pytest tests/llm_eval/ -v --model=qwen/qwen3-8b
"""

import os
import pytest
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env
load_dotenv()


def pytest_addoption(parser):
    """Add --model option for selecting OpenRouter model to test."""
    parser.addoption(
        "--model",
        action="store",
        default="qwen/qwen3-8b",
        help="OpenRouter model ID to evaluate (e.g., qwen/qwen3-8b, liquid/lfm2-8b-a1b)",
    )


@pytest.fixture
def model(request) -> str:
    """Get the model ID from command line."""
    return request.config.getoption("--model")


@pytest.fixture
def client() -> OpenAI:
    """Create OpenAI client configured for OpenRouter."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY environment variable not set")

    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
