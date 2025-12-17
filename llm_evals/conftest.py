"""Pytest configuration for LLM evaluation tests."""

import os
import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "requires_google_api: mark test as requiring GOOGLE_API_KEY"
    )
    config.addinivalue_line(
        "markers", "requires_llm_api: mark test as requiring an LLM API key"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (makes API calls)"
    )


@pytest.fixture(scope="session")
def google_api_available():
    """Check if Google API is available."""
    return bool(os.getenv("GOOGLE_API_KEY"))


@pytest.fixture(scope="session")
def llm_api_available():
    """Check if any LLM API is available."""
    return any([
        os.getenv("ANTHROPIC_API_KEY"),
        os.getenv("CEREBRAS_API_KEY"),
        os.getenv("OPENROUTER_API_KEY"),
        os.getenv("OPENAI_API_KEY"),
    ])


@pytest.fixture(autouse=True)
def skip_if_no_google_api(request, google_api_available):
    """Skip tests marked with requires_google_api if key not set."""
    if request.node.get_closest_marker("requires_google_api"):
        if not google_api_available:
            pytest.skip("GOOGLE_API_KEY not set")


@pytest.fixture(autouse=True)
def skip_if_no_llm_api(request, llm_api_available):
    """Skip tests marked with requires_llm_api if no key set."""
    if request.node.get_closest_marker("requires_llm_api"):
        if not llm_api_available:
            pytest.skip("No LLM API key set")
