#!/usr/bin/env python3
"""
CLI for generating children's stories.

Usage:
    python scripts/generate_story.py "teach about sharing"
    python scripts/generate_story.py "explain photosynthesis" --output custom_name.md
    python scripts/generate_story.py "the importance of kindness" --fast
    python scripts/generate_story.py "recycling" --stdout  # print to terminal instead of file
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import configure_dspy, STORY_CONSTANTS
from backend.core.programs.story_generator import StoryGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Generate children's picture book stories from learning goals",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/generate_story.py "teach about sharing"
    python scripts/generate_story.py "explain how rainbows form" --age 5-8
    python scripts/generate_story.py "the value of friendship" --output my_story.md
    python scripts/generate_story.py "teach about recycling" --fast
    python scripts/generate_story.py "kindness" --stdout
        """,
    )

    parser.add_argument(
        "goal",
        type=str,
        help="The learning goal or theme for the story",
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file name (saved to output/ directory). Auto-generated if not specified.",
    )

    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print to terminal instead of saving to file",
    )

    parser.add_argument(
        "--age",
        type=str,
        default="4-7",
        help="Target age range (default: 4-7)",
    )

    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip quality iteration loop (faster, single attempt)",
    )

    parser.add_argument(
        "--quality-threshold",
        type=int,
        default=7,
        help="Minimum quality score to accept (1-10, default: 7)",
    )

    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Maximum generation attempts (default: 3)",
    )

    parser.add_argument(
        "--words-per-page",
        type=int,
        default=35,
        help="Target words per page (default: 35)",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print progress information",
    )

    args = parser.parse_args()

    # Configure DSPy with inference LM
    if args.verbose:
        print("Configuring DSPy...")
    configure_dspy(use_reflection_lm=False)

    # Create generator
    generator = StoryGenerator(
        quality_threshold=args.quality_threshold,
        max_attempts=args.max_attempts,
        words_per_page=args.words_per_page,
    )

    # Generate story
    if args.verbose:
        print(f"Generating story for goal: {args.goal}")
        print(f"Target age range: {args.age}")

    if args.fast:
        story = generator.generate_simple(args.goal)
    else:
        story = generator.forward(
            goal=args.goal,
            target_age_range=args.age,
        )

    # Output result
    formatted = story.to_formatted_string()

    if args.stdout:
        print(formatted)
    else:
        # Determine output path
        output_dir = Path(__file__).parent.parent / "output"
        output_dir.mkdir(exist_ok=True)

        if args.output:
            filename = args.output if args.output.endswith(".md") else f"{args.output}.md"
        else:
            # Auto-generate filename from goal and timestamp
            slug = re.sub(r"[^a-z0-9]+", "_", args.goal.lower())[:30].strip("_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{slug}_{timestamp}.md"

        output_path = output_dir / filename
        output_path.write_text(formatted)
        print(f"Story saved to: {output_path}")

    # Print summary if verbose
    if args.verbose:
        print("\n--- Generation Summary ---")
        print(f"Title: {story.title}")
        print(f"Pages: {story.page_count}")
        print(f"Word count: {story.word_count}")
        print(f"Attempts: {story.attempts}")
        if story.judgment:
            print(f"Quality score: {story.judgment.overall_score}/10")
            print(f"Verdict: {story.judgment.verdict}")


if __name__ == "__main__":
    main()
