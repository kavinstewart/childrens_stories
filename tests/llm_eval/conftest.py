"""
Pytest configuration for LLM evaluation tests.

Usage:
    # OpenRouter tests (disambiguation)
    poetry run pytest tests/llm_eval/ -v --model=qwen/qwen3-8b

    # DSPy tests (entity format)
    poetry run pytest tests/llm_eval/test_entity_format.py -v --dspy-model=anthropic/claude-sonnet-4-5-20250929
"""

import os
from typing import Optional

import pytest
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env
load_dotenv()


def pytest_addoption(parser):
    """Add model options for selecting LLMs to test."""
    parser.addoption(
        "--model",
        action="store",
        default="qwen/qwen3-8b",
        help="OpenRouter model ID to evaluate (e.g., qwen/qwen3-8b, liquid/lfm2-8b-a1b)",
    )
    parser.addoption(
        "--dspy-model",
        action="store",
        default=None,
        help="DSPy model ID to evaluate (e.g., gemini/gemini-3-pro-preview, anthropic/claude-opus-4-5-20251101)",
    )


@pytest.fixture
def model(request) -> str:
    """Get the OpenRouter model ID from command line."""
    return request.config.getoption("--model")


@pytest.fixture
def dspy_model(request) -> Optional[str]:
    """Get the DSPy model ID from command line."""
    return request.config.getoption("--dspy-model")


@pytest.fixture
def dspy_lm(dspy_model: Optional[str]):
    """
    Create a DSPy LM for the specified model.

    If --dspy-model is not specified, uses the default provider priority
    from backend/config/llm.py (GOOGLE > ANTHROPIC > OPENAI).
    """
    import dspy

    if dspy_model is None:
        # Use default provider priority
        from backend.config.llm import get_inference_lm
        try:
            return get_inference_lm()
        except ValueError:
            pytest.skip("No API key found for DSPy models")

    # Determine API key based on model prefix
    if dspy_model.startswith("gemini/"):
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            pytest.skip("GOOGLE_API_KEY not set for gemini model")
    elif dspy_model.startswith("anthropic/"):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not set for anthropic model")
    elif dspy_model.startswith("openai/") or dspy_model.startswith("gpt"):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set for openai model")
    else:
        pytest.skip(f"Unknown model prefix for {dspy_model}")

    return dspy.LM(
        dspy_model,
        api_key=api_key,
        max_tokens=4096,
        temperature=1.0,
        timeout=120,
    )


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
