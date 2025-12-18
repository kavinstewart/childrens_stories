#!/usr/bin/env python3
"""Debug script to see raw model output for page generation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import configure_dspy
from backend.core.modules.outline_generator import OutlineGenerator
from backend.core.signatures.page_writer import PageWriterSignature
import dspy

# Configure
configure_dspy()

# Generate outline first
outline_gen = OutlineGenerator()
outline = outline_gen(goal="teach about sharing")

print("=== OUTLINE ===")
print(f"Title: {outline.title}")
print(f"Characters: {outline.characters}")
print(f"\nRaw page_breakdown:\n{outline.page_breakdown}")
print(f"\nParsed pages: {outline.get_pages()}")

# Try to generate just page 2 (one that failed)
print("\n=== GENERATING PAGE 2 ===")
page_spec = outline.get_pages()[1]["content"]
print(f"Page spec: {page_spec}")

writer = dspy.ChainOfThought(PageWriterSignature)
result = writer(
    story_title=outline.title,
    characters=outline.characters,
    setting=outline.setting,
    page_number=2,
    total_pages=12,
    page_spec=page_spec,
    previous_text="",
    target_word_count=35,
)

print(f"\nResult page_text: {result.page_text!r}")
print(f"Result illustration_prompt: {result.illustration_prompt!r}")

# Check LM history
print("\n=== LM HISTORY ===")
lm = dspy.settings.lm
if hasattr(lm, 'history') and lm.history:
    last_call = lm.history[-1]
    print(f"Last prompt: {last_call.get('prompt', 'N/A')[:500]}...")
    print(f"Last response: {last_call.get('response', 'N/A')[:1000]}...")
else:
    print("No history available")
