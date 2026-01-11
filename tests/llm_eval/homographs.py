"""
Homograph data for LLM evaluation.

Re-exports from backend.core.homographs - the canonical source.
"""

from backend.core.homographs import (
    HOMOGRAPHS,
    HomographEntry,
    get_disambiguation_prompt,
)

__all__ = ["HOMOGRAPHS", "HomographEntry", "get_disambiguation_prompt"]
