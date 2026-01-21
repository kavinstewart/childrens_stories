"""Root pytest configuration for shared markers."""


def pytest_configure(config):
    """Register custom markers used across test directories."""
    config.addinivalue_line(
        "markers", "requires_google_api: mark test as requiring GOOGLE_API_KEY"
    )
    config.addinivalue_line(
        "markers", "requires_llm_api: mark test as requiring an LLM API key"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (makes API calls)"
    )
