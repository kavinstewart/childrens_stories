"""
LLM evaluation tests that make real API calls.

These tests are slow and costly - run selectively:
    poetry run pytest llm_evals/ -v

Requires API keys in .env:
    - GOOGLE_API_KEY (for image generation)
    - ANTHROPIC_API_KEY or CEREBRAS_API_KEY (for text generation)
"""
