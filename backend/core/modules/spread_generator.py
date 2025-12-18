"""
DSPy Module for generating all story spreads in a single call.

This replaces the page-by-page generation approach with a more coherent
single-call approach that generates all 12 spreads at once.
"""

import re
import dspy

from ..types import StoryOutline, StorySpread
from ..signatures.full_story import FullStorySignature, FullStoryWithPromptsSignature


class SpreadGenerator(dspy.Module):
    """
    Generate all spreads of a children's story in a single LLM call.

    This approach produces more coherent narratives than page-by-page
    generation because the model can see and plan the entire story arc.
    """

    def __init__(self, include_illustration_prompts: bool = True):
        super().__init__()
        self.include_illustration_prompts = include_illustration_prompts

        if include_illustration_prompts:
            self.generate = dspy.ChainOfThought(FullStoryWithPromptsSignature)
        else:
            self.generate = dspy.ChainOfThought(FullStorySignature)

    def _format_outline_for_generation(self, outline: StoryOutline) -> str:
        """Format the outline as context for story generation."""
        parts = [
            f"TITLE: {outline.title}",
            f"\nPROTAGONIST GOAL: {outline.protagonist_goal}",
            f"\nSTAKES: {outline.stakes}",
            f"\nCHARACTERS:\n{outline.characters}",
            f"\nSETTING: {outline.setting}",
            f"\nEMOTIONAL ARC: {outline.emotional_arc}",
            f"\nPLOT SUMMARY:\n{outline.plot_summary}",
            f"\nSPREAD-BY-SPREAD PLAN:\n{outline.spread_breakdown}",
            f"\nIMPLICIT MORAL (never state aloud): {outline.moral}",
        ]

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
