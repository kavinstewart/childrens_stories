"""Tests for cost calculator module."""

import pytest
from decimal import Decimal

from backend.core.cost_calculator import (
    calculate_cost,
    get_model_pricing,
    PRICING,
)


class TestPricing:
    """Tests for pricing data."""

    def test_gemini_3_pro_pricing_exists(self):
        """Gemini 3 Pro has pricing defined."""
        pricing = get_model_pricing("gemini-3-pro-preview")
        assert "input" in pricing
        assert "output" in pricing
        assert isinstance(pricing["input"], Decimal)
        assert isinstance(pricing["output"], Decimal)

    def test_claude_pricing_exists(self):
        """Claude Opus 4.5 has pricing defined."""
        pricing = get_model_pricing("claude-opus-4-5-20251101")
        assert "input" in pricing
        assert "output" in pricing

    def test_image_model_pricing_exists(self):
        """Image models have per_image pricing."""
        pricing = get_model_pricing("gemini-3-pro-image-preview")
        assert "per_image" in pricing
        assert isinstance(pricing["per_image"], Decimal)

    def test_unknown_model_returns_empty(self):
        """Unknown models return empty dict."""
        pricing = get_model_pricing("unknown-model")
        assert pricing == {}


class TestCalculateCost:
    """Tests for calculate_cost function."""

    def test_llm_only_cost(self):
        """Calculate cost for LLM tokens only."""
        usage = {
            "llm_input_tokens": 1000,
            "llm_output_tokens": 500,
            "llm_model": "gemini-3-pro-preview",
            "llm_calls": 3,
            "image_count": 0,
            "image_model": "",
            "image_retries": 0,
        }
        cost = calculate_cost(usage)
        # Gemini 3 Pro: $0.00025/1K input, $0.001/1K output
        # (1000 * 0.00025 / 1000) + (500 * 0.001 / 1000) = 0.00025 + 0.0005 = 0.00075
        assert cost == Decimal("0.00075")

    def test_image_only_cost(self):
        """Calculate cost for images only."""
        usage = {
            "llm_input_tokens": 0,
            "llm_output_tokens": 0,
            "llm_model": "",
            "llm_calls": 0,
            "image_count": 12,
            "image_model": "gemini-3-pro-image-preview",
            "image_retries": 2,
        }
        cost = calculate_cost(usage)
        # 12 images at $0.02/image = $0.24
        assert cost == Decimal("0.24")

    def test_combined_cost(self):
        """Calculate cost for LLM + images."""
        usage = {
            "llm_input_tokens": 10000,
            "llm_output_tokens": 5000,
            "llm_model": "gemini-3-pro-preview",
            "llm_calls": 5,
            "image_count": 12,
            "image_model": "gemini-3-pro-image-preview",
            "image_retries": 0,
        }
        cost = calculate_cost(usage)
        # LLM: (10000 * 0.00025 / 1000) + (5000 * 0.001 / 1000) = 0.0025 + 0.005 = 0.0075
        # Images: 12 * 0.02 = 0.24
        # Total: 0.2475
        assert cost == Decimal("0.2475")

    def test_unknown_llm_model_zero_cost(self):
        """Unknown LLM model results in zero LLM cost."""
        usage = {
            "llm_input_tokens": 1000,
            "llm_output_tokens": 500,
            "llm_model": "unknown-model",
            "llm_calls": 1,
            "image_count": 0,
            "image_model": "",
            "image_retries": 0,
        }
        cost = calculate_cost(usage)
        assert cost == Decimal("0")

    def test_unknown_image_model_zero_cost(self):
        """Unknown image model results in zero image cost."""
        usage = {
            "llm_input_tokens": 0,
            "llm_output_tokens": 0,
            "llm_model": "",
            "llm_calls": 0,
            "image_count": 12,
            "image_model": "unknown-image-model",
            "image_retries": 0,
        }
        cost = calculate_cost(usage)
        assert cost == Decimal("0")

    def test_empty_usage_zero_cost(self):
        """Empty usage results in zero cost."""
        usage = {
            "llm_input_tokens": 0,
            "llm_output_tokens": 0,
            "llm_model": "",
            "llm_calls": 0,
            "image_count": 0,
            "image_model": "",
            "image_retries": 0,
        }
        cost = calculate_cost(usage)
        assert cost == Decimal("0")

    def test_retries_included_in_image_count(self):
        """Image retries are counted in image_count (already billed)."""
        # image_count includes all images generated, including retries
        # Retries are tracked separately for analytics but cost is based on total count
        usage = {
            "llm_input_tokens": 0,
            "llm_output_tokens": 0,
            "llm_model": "",
            "llm_calls": 0,
            "image_count": 14,  # 12 spreads + 2 retries
            "image_model": "gemini-3-pro-image-preview",
            "image_retries": 2,
        }
        cost = calculate_cost(usage)
        # 14 images at $0.02/image = $0.28
        assert cost == Decimal("0.28")

    def test_claude_opus_cost(self):
        """Calculate cost for Claude Opus 4.5."""
        usage = {
            "llm_input_tokens": 1000,
            "llm_output_tokens": 500,
            "llm_model": "claude-opus-4-5-20251101",
            "llm_calls": 1,
            "image_count": 0,
            "image_model": "",
            "image_retries": 0,
        }
        cost = calculate_cost(usage)
        # Claude Opus 4.5: $0.015/1K input, $0.075/1K output
        # (1000 * 0.015 / 1000) + (500 * 0.075 / 1000) = 0.015 + 0.0375 = 0.0525
        assert cost == Decimal("0.0525")

    def test_flash_image_model_cost(self):
        """Calculate cost for flash image model (cheaper)."""
        usage = {
            "llm_input_tokens": 0,
            "llm_output_tokens": 0,
            "llm_model": "",
            "llm_calls": 0,
            "image_count": 12,
            "image_model": "gemini-3-flash-preview",
            "image_retries": 0,
        }
        cost = calculate_cost(usage)
        # 12 images at $0.002/image = $0.024
        assert cost == Decimal("0.024")
