"""
Cost calculation for story generation.

Pure functions for computing costs from usage data.
Pricing is the single source of truth for model rates.
"""

from decimal import Decimal
from typing import Optional


# Pricing per 1K tokens for LLM models, per image for image models
# Update these when pricing changes
PRICING: dict[str, dict[str, Decimal]] = {
    # LLM models (input/output per 1K tokens)
    "gemini-3-pro-preview": {
        "input": Decimal("0.00025"),   # $0.25 per 1M input tokens
        "output": Decimal("0.001"),    # $1.00 per 1M output tokens
    },
    "claude-opus-4-5-20251101": {
        "input": Decimal("0.015"),     # $15 per 1M input tokens
        "output": Decimal("0.075"),    # $75 per 1M output tokens
    },
    "claude-sonnet-4-20250514": {
        "input": Decimal("0.003"),     # $3 per 1M input tokens
        "output": Decimal("0.015"),    # $15 per 1M output tokens
    },
    "gpt-5.2": {
        "input": Decimal("0.010"),     # $10 per 1M input tokens
        "output": Decimal("0.030"),    # $30 per 1M output tokens
    },
    # Image models (per image)
    "gemini-3-pro-image-preview": {
        "per_image": Decimal("0.02"),  # $0.02 per image
    },
    "gemini-3-flash-preview": {
        "per_image": Decimal("0.002"), # $0.002 per image
    },
}


def get_model_pricing(model: str) -> dict[str, Decimal]:
    """
    Get pricing for a model.

    Args:
        model: Model identifier (e.g., "gemini-3-pro-preview")

    Returns:
        Dict with pricing info, or empty dict if unknown model
    """
    return PRICING.get(model, {})


def calculate_cost(usage: dict) -> Decimal:
    """
    Calculate total cost from usage data.

    Args:
        usage: Dict with keys:
            - llm_input_tokens: int
            - llm_output_tokens: int
            - llm_model: str
            - image_count: int
            - image_model: str

    Returns:
        Total cost as Decimal (USD)
    """
    total = Decimal("0")

    # LLM cost
    llm_model = usage.get("llm_model", "")
    if llm_model:
        pricing = get_model_pricing(llm_model)
        if "input" in pricing and "output" in pricing:
            input_tokens = usage.get("llm_input_tokens", 0)
            output_tokens = usage.get("llm_output_tokens", 0)
            # Price is per 1K tokens
            total += (Decimal(input_tokens) * pricing["input"]) / 1000
            total += (Decimal(output_tokens) * pricing["output"]) / 1000

    # Image cost
    image_model = usage.get("image_model", "")
    if image_model:
        pricing = get_model_pricing(image_model)
        if "per_image" in pricing:
            image_count = usage.get("image_count", 0)
            total += Decimal(image_count) * pricing["per_image"]

    return total
