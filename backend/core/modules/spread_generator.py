"""
DSPy Module for generating all story spreads in a single call.

DEPRECATED: This module is part of the outline-first workflow. Use
DirectStoryGenerator instead for the story-first workflow that generates
stories directly from a goal without an intermediate outline step.
"""

import re
import warnings
import dspy

from ..types import StoryOutline, StorySpread
from ..signatures.full_story import FullStorySignature, FullStoryWithPromptsSignature
from ..reference_stories import get_random_examples


class SpreadGenerator(dspy.Module):
    """
    Generate all spreads of a children's story in a single LLM call.

    DEPRECATED: Use DirectStoryGenerator instead for the story-first workflow.
    This module requires an outline from OutlineGenerator which can invent
    characters that don't appear in the final story.
    """

    def __init__(
        self,
        include_illustration_prompts: bool = True,
        include_examples: bool = True,
        example_count: int = 1,
    ):
        warnings.warn(
            "SpreadGenerator is deprecated. Use DirectStoryGenerator for the story-first workflow.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__()
        self.include_illustration_prompts = include_illustration_prompts
        self.include_examples = include_examples
        self.example_count = example_count

        if include_illustration_prompts:
            self.generate = dspy.ChainOfThought(FullStoryWithPromptsSignature)
        else:
            self.generate = dspy.ChainOfThought(FullStorySignature)

    def _format_outline_for_generation(self, outline: StoryOutline) -> str:
        """Format the outline as context for story generation."""
        parts = []

        # Include reference examples at the start if enabled
        if self.include_examples and self.example_count > 0:
            examples = get_random_examples(count=self.example_count)
            parts.append("REFERENCE EXAMPLES OF EXCELLENT CHILDREN'S PICTURE BOOK PROSE:")
            parts.append("Study these examples for rhythm, sentence length, and read-aloud quality.\n")
            for example in examples:
                parts.append(f'--- "{example.title}" by {example.author} ---')
                parts.append(example.text)
                parts.append(f"--- End of example ({example.word_count} words) ---\n")
            parts.append("=" * 60)
            parts.append("NOW WRITE YOUR STORY BASED ON THIS OUTLINE:")
            parts.append("=" * 60 + "\n")

        # Add the story outline
        parts.append(f"TITLE: {outline.title}")
        parts.append(f"\nCHARACTERS:\n{outline.characters}")
        parts.append(f"\nSETTING: {outline.setting}")
        parts.append(f"\nPLOT:\n{outline.plot_summary}")
        parts.append(f"\nSPREAD-BY-SPREAD PLAN:\n{outline.spread_breakdown}")

        # Add character visual descriptions if available
        if outline.character_bibles:
            parts.append("\nCHARACTER VISUAL DETAILS:")
            for bible in outline.character_bibles:
                parts.append(f"- {bible.to_prompt_string()}")

        # Add illustration style if selected
        if outline.illustration_style:
            parts.append(f"\nILLUSTRATION STYLE: {outline.illustration_style.name}")
            parts.append(f"Style description: {outline.illustration_style.description}")

        return "\n".join(parts)

    def _parse_spreads(self, raw_output: str) -> list[StorySpread]:
        """Parse the raw LLM output into StorySpread objects."""
        spreads = []

        # Handle both formats: with and without illustration prompts
        # Pattern matches "Spread N:" followed by text
        spread_pattern = r'Spread\s+(\d+):\s*(.+?)(?=Spread\s+\d+:|$|\[Illustration:)'
        illustration_pattern = r'\[Illustration:\s*(.+?)\]'

        # First, try to extract spreads with their text
        matches = re.findall(spread_pattern, raw_output, re.DOTALL | re.IGNORECASE)

        if not matches:
            # Fallback: try splitting by "Spread N:"
            lines = raw_output.strip().split('\n')
            current_spread_num = 0
            current_text = []

            for line in lines:
                line = line.strip()
                spread_match = re.match(r'Spread\s+(\d+):\s*(.*)', line, re.IGNORECASE)

                if spread_match:
                    # Save previous spread if exists
                    if current_spread_num > 0 and current_text:
                        text = ' '.join(current_text).strip()
                        # Remove illustration prompt from text if present
                        text = re.sub(r'\[Illustration:.*?\]', '', text).strip()
                        spreads.append(StorySpread(
                            spread_number=current_spread_num,
                            text=text,
                            word_count=len(text.split()),
                        ))

                    current_spread_num = int(spread_match.group(1))
                    current_text = [spread_match.group(2)] if spread_match.group(2) else []
                elif current_spread_num > 0:
                    # Skip illustration prompts in text
                    if not line.startswith('[Illustration:'):
                        current_text.append(line)

            # Don't forget the last spread
            if current_spread_num > 0 and current_text:
                text = ' '.join(current_text).strip()
                text = re.sub(r'\[Illustration:.*?\]', '', text).strip()
                spreads.append(StorySpread(
                    spread_number=current_spread_num,
                    text=text,
                    word_count=len(text.split()),
                ))
        else:
            # Process regex matches
            for spread_num_str, text in matches:
                spread_num = int(spread_num_str)
                text = text.strip()

                # Extract illustration prompt if present
                illust_match = re.search(illustration_pattern, raw_output[raw_output.find(f"Spread {spread_num}"):], re.DOTALL)
                illustration_prompt = illust_match.group(1).strip() if illust_match else ""

                # Clean text of any remaining illustration markers
                text = re.sub(r'\[Illustration:.*?\]', '', text, flags=re.DOTALL).strip()

                spreads.append(StorySpread(
                    spread_number=spread_num,
                    text=text,
                    word_count=len(text.split()),
                    illustration_prompt=illustration_prompt,
                ))

        # Sort by spread number
        spreads.sort(key=lambda s: s.spread_number)

        return spreads

    def _parse_spreads_with_prompts(self, raw_output: str) -> list[StorySpread]:
        """Parse output that includes illustration prompts."""
        spreads = []

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

            text = content.strip()

            spreads.append(StorySpread(
                spread_number=spread_num,
                text=text,
                word_count=len(text.split()),
                illustration_prompt=illustration_prompt,
            ))

        # Sort by spread number
        spreads.sort(key=lambda s: s.spread_number)

        return spreads

    def forward(self, outline: StoryOutline, debug: bool = False) -> list[StorySpread]:
        """
        Generate all spreads for a story from the outline.

        Args:
            outline: The complete story outline
            debug: If True, print debug info

        Returns:
            List of StorySpread objects (typically 12)
        """
        import sys

        # Format outline for the signature
        formatted_outline = self._format_outline_for_generation(outline)

        if debug:
            print(f"DEBUG Generating spreads for: {outline.title}", file=sys.stderr)

        # Single LLM call to generate all spreads
        if self.include_illustration_prompts:
            result = self.generate(outline=formatted_outline)
            raw_output = result.story_with_prompts
            spreads = self._parse_spreads_with_prompts(raw_output)
        else:
            result = self.generate(outline=formatted_outline)
            raw_output = result.story
            spreads = self._parse_spreads(raw_output)

        if debug:
            print(f"DEBUG Generated {len(spreads)} spreads", file=sys.stderr)
            total_words = sum(s.word_count for s in spreads)
            print(f"DEBUG Total word count: {total_words}", file=sys.stderr)

        # Validate we got 12 spreads
        if len(spreads) != 12:
            print(f"WARNING: Expected 12 spreads, got {len(spreads)}", file=sys.stderr)
            if debug:
                print(f"DEBUG Raw output:\n{raw_output[:1000]}...", file=sys.stderr)

        return spreads

    def generate_all_spreads(
        self, outline: StoryOutline, debug: bool = False
    ) -> list[StorySpread]:
        """
        Alias for forward() for API compatibility with PageGenerator.generate_all_pages().
        """
        return self.forward(outline, debug=debug)


# Backwards compatibility alias
PageGenerator = SpreadGenerator
