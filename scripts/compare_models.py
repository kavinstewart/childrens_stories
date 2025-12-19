#!/usr/bin/env python3
"""Compare story generation across different models."""

import os
import sys
sys.path.insert(0, '/Users/kavinstewart/Desktop/projects/childrens_stories')

from dotenv import load_dotenv
load_dotenv('/Users/kavinstewart/Desktop/projects/childrens_stories/.env')

import dspy
from backend.core.programs.story_generator import StoryGenerator

goal = "a story that teaches kids that feedback is frustrating to receive but that it's super important to be able to get it in order to improve"

model_name = sys.argv[1] if len(sys.argv) > 1 else "gemini"

if model_name == "gemini":
    print("Generating with Gemini 3 Pro...", file=sys.stderr)
    lm = dspy.LM(
        "gemini/gemini-3-pro-preview",
        api_key=os.getenv("GOOGLE_API_KEY"),
        max_tokens=4096,
        temperature=0.7,
    )
elif model_name == "gpt":
    print("Generating with GPT-5.2...", file=sys.stderr)
    lm = dspy.LM(
        "gpt-5.2",
        api_key=os.getenv("OPENAI_API_KEY"),
        max_tokens=16000,
        temperature=1.0,
    )
else:
    print(f"Unknown model: {model_name}", file=sys.stderr)
    sys.exit(1)

generator = StoryGenerator(quality_threshold=7, max_attempts=1, lm=lm)
story = generator.forward(goal=goal, target_age_range="4-7", skip_quality_loop=True)

print(f"\n{'='*60}")
print(f"  {story.title.upper()}")
print(f"  Model: {model_name}")
print(f"{'='*60}")
print(f"Word count: {story.word_count}")
print()
for spread in story.spreads:
    text = spread.text.replace('**', '').strip()
    print(text)
    print()
