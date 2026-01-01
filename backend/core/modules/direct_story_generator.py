"""
DSPy Module for generating stories directly from a goal.

Story-first workflow: generate the complete story in one shot,
then extract characters afterward. This replaces the outline-first
approach which invented characters before the story existed.
"""

import re
import dspy

from ..types import StorySpread
from ..signatures.direct_story import DirectStorySignature
from ..reference_stories import get_random_examples


class DirectStoryGenerator(dspy.Module):
    """
    Generate a complete children's story directly from a goal.

    This is the story-first approach: write the story first, then
    extract what characters and settings emerged. This produces
    more natural stories without invented-but-unused characters.

    Args:
        include_examples: Whether to include reference story examples
        example_count: Number of reference examples to include (1-2 recommended)
    """

    def __init__(
        self,
        include_examples: bool = True,
        example_count: int = 1,
    ):
        super().__init__()
        self.include_examples = include_examples
        self.example_count = example_count
        self.generate = dspy.ChainOfThought(DirectStorySignature)

    def _format_examples(self) -> str:
        """Get formatted reference examples for the prompt."""
        if not self.include_examples or self.example_count == 0:
            return "No reference examples provided."

        examples = get_random_examples(count=self.example_count)
        parts = [
            "Study these examples for rhythm, sentence length, and read-aloud quality.",
            "Pay special attention to HOW THEY END—notice they don't explain, they just land:\n"
        ]

        for example in examples:
            parts.append(f'--- "{example.title}" by {example.author} ---')
            parts.append(example.text)
            parts.append(f"--- End ({example.word_count} words) ---\n")

        return "\n".join(parts)

    def _parse_characters_field(self, characters_str: str) -> list[str] | None:
        """
        Parse the [Characters: ...] field into a list of character names.

        Returns:
            List of character names, empty list if "none", or None if not parseable.
        """
        if not characters_str:
            return None

        characters_str = characters_str.strip()

        # Handle explicit "none" or empty
        if characters_str.lower() in ("none", "n/a", "no one", "nobody", "empty", ""):
            return []

        # Split by comma and clean up
        names = [name.strip() for name in characters_str.split(",")]
        # Filter out empty strings and "none" values
        names = [n for n in names if n and n.lower() not in ("none", "n/a")]

        return names if names else []

    def _parse_story_output(self, raw_output: str) -> tuple[str, list[StorySpread]]:
        """
        Parse the raw LLM output into title and spreads.

        Validates that [Characters:] field is present for each spread.
        Emits warnings for missing fields but continues with None (fallback path).

        Returns:
            Tuple of (title, list of StorySpread objects)
        """
        import sys

        # Extract title
        title_match = re.search(r'TITLE:\s*(.+?)(?:\n|$)', raw_output, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else "Untitled Story"

        # Parse spreads
        spreads = []
        missing_characters_spreads = []  # Track spreads missing [Characters:] field

        # Split by "Spread N:" markers
        parts = re.split(r'(?=Spread\s+\d+:)', raw_output, flags=re.IGNORECASE)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Extract spread number
            num_match = re.match(r'Spread\s+(\d+):\s*(.*)', part, re.DOTALL | re.IGNORECASE)
            if not num_match:
                continue

            spread_num = int(num_match.group(1))
            content = num_match.group(2).strip()

            # Extract illustration prompt if present
            illust_match = re.search(r'\[Illustration:\s*(.+?)\]', content, re.DOTALL)
            illustration_prompt = ""
            if illust_match:
                illustration_prompt = illust_match.group(1).strip()
                # Remove illustration prompt from text
                content = content[:illust_match.start()] + content[illust_match.end():]

            # Extract present characters - REQUIRED field
            present_characters = None
            chars_match = re.search(r'\[Characters:\s*(.+?)\]', content, re.DOTALL)
            if chars_match:
                present_characters = self._parse_characters_field(chars_match.group(1))
                # Remove characters field from text
                content = content[:chars_match.start()] + content[chars_match.end():]
            else:
                # Track missing [Characters:] for warning
                missing_characters_spreads.append(spread_num)

            text = content.strip()

            spreads.append(StorySpread(
                spread_number=spread_num,
                text=text,
                word_count=len(text.split()),
                illustration_prompt=illustration_prompt,
                present_characters=present_characters,
            ))

        # Sort by spread number
        spreads.sort(key=lambda s: s.spread_number)

        # Emit warning if any spreads are missing [Characters:] field
        if missing_characters_spreads:
            print(
                f"WARNING: [Characters:] field missing from {len(missing_characters_spreads)} spread(s): "
                f"{missing_characters_spreads}. Illustration will use fallback character detection "
                f"which may be less accurate. Consider regenerating the story.",
                file=sys.stderr
            )

        return title, spreads

    def forward(self, goal: str, debug: bool = False) -> tuple[str, list[StorySpread]]:
        """
        Generate a complete story from the given goal.

        Args:
            goal: The theme, concept, or learning goal for the story
            debug: If True, print debug info

        Returns:
            Tuple of (title, list of StorySpread objects)
        """
        import sys

        # Get reference examples
        reference_examples = self._format_examples()

        if debug:
            print(f"DEBUG Generating story for goal: {goal[:50]}...", file=sys.stderr)

        # Single LLM call to generate the complete story
        result = self.generate(
            goal=goal,
            reference_examples=reference_examples,
        )

        # Parse the output
        title, spreads = self._parse_story_output(result.story)

        if debug:
            print(f"DEBUG Generated: '{title}' with {len(spreads)} spreads", file=sys.stderr)
            total_words = sum(s.word_count for s in spreads)
            print(f"DEBUG Total word count: {total_words}", file=sys.stderr)

        # Validate we got 12 spreads
        if len(spreads) != 12:
            print(f"WARNING: Expected 12 spreads, got {len(spreads)}", file=sys.stderr)

        return title, spreads
