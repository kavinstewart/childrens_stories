"""
LLM evaluation tests for homograph disambiguation.

Runs 545+ test cases against a specified model via OpenRouter to measure accuracy.

Usage:
    # Test a single model
    poetry run pytest tests/llm_eval/test_disambiguation.py -v --model=qwen/qwen3-8b

    # Run with summary only (faster output)
    poetry run pytest tests/llm_eval/test_disambiguation.py --model=qwen/qwen3-8b --tb=no -q

    # Test specific homograph
    poetry run pytest tests/llm_eval/test_disambiguation.py -v --model=qwen/qwen3-8b -k "read"
"""

import re
import time
import pytest
from openai import OpenAI

from .test_cases import TEST_CASES, STANDARD_CASES, EDGE_CASES
from .homographs import get_disambiguation_prompt


def parse_response(response_text: str) -> int | None:
    """
    Parse the model's response to extract 0 or 1.
    Returns None if parsing fails.
    """
    text = response_text.strip()

    # Direct match
    if text == "0":
        return 0
    if text == "1":
        return 1

    # Look for 0 or 1 at the start
    if text.startswith("0"):
        return 0
    if text.startswith("1"):
        return 1

    # Search for standalone 0 or 1
    match = re.search(r"\b([01])\b", text)
    if match:
        return int(match.group(1))

    return None


def normalize_case(case: tuple) -> tuple[str, str, int, int]:
    """Normalize a test case to always have 4 elements (sentence, word, expected, occurrence)."""
    if len(case) == 3:
        return (case[0], case[1], case[2], 1)  # Default occurrence = 1
    return case


def make_test_id(case: tuple) -> str:
    """Generate a readable test ID from a test case."""
    normalized = normalize_case(case)
    sentence, word, expected, occurrence = normalized
    # Truncate sentence for readability
    short_sentence = sentence[:40] + "..." if len(sentence) > 40 else sentence
    occ_str = f"@{occurrence}" if occurrence > 1 else ""
    return f"{word}[{expected}]{occ_str}-{short_sentence}"


@pytest.mark.parametrize(
    "case",
    TEST_CASES,
    ids=[make_test_id(c) for c in TEST_CASES],
)
def test_disambiguation(
    case: tuple,
    model: str,
    client: OpenAI,
):
    """Test that the model correctly disambiguates a homograph in context."""
    sentence, word, expected, occurrence = normalize_case(case)
    prompt = get_disambiguation_prompt(word, sentence, occurrence=occurrence)
    assert prompt is not None, f"Word '{word}' not found in homographs dictionary"

    # Small delay to avoid rate limiting
    time.sleep(0.2)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=16,
            temperature=0,
        )
        response_text = response.choices[0].message.content or ""
        result = parse_response(response_text)

        assert result is not None, (
            f"Could not parse response: '{response_text}'\n"
            f"Prompt: {prompt}"
        )
        assert result == expected, (
            f"Expected {expected}, got {result}\n"
            f"Word: '{word}' (occurrence {occurrence}) in sentence: '{sentence}'\n"
            f"Response: '{response_text}'"
        )

    except Exception as e:
        pytest.fail(f"API call failed: {e}\nModel: {model}\nPrompt: {prompt}")


# Subset tests for quick validation
@pytest.mark.parametrize(
    "case",
    STANDARD_CASES[:50],  # First 50 standard cases
    ids=[make_test_id(c) for c in STANDARD_CASES[:50]],
)
def test_disambiguation_quick(
    case: tuple,
    model: str,
    client: OpenAI,
):
    """Quick test with subset of cases for fast validation."""
    sentence, word, expected, occurrence = normalize_case(case)
    prompt = get_disambiguation_prompt(word, sentence, occurrence=occurrence)
    assert prompt is not None

    # Small delay to avoid rate limiting
    time.sleep(0.2)

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=16,
        temperature=0,
    )
    response_text = response.choices[0].message.content or ""
    result = parse_response(response_text)

    assert result == expected, f"Expected {expected}, got {result} for '{word}'"
