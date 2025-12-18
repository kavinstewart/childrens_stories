"""
DSPy Module for generating story outlines.
"""

import dspy
import re

from ..types import CharacterBible, StoryOutline
from ..signatures.story_outline import StoryOutlineSignature
from ..signatures.character_bible import CharacterBibleSignature
from ..signatures.illustration_style import IllustrationStyleSignature
from .illustration_styles import (
    get_style_by_name,
    get_all_styles_for_selection,
)


class OutlineGenerator(dspy.Module):
    """
    Generate a structured story outline from a learning goal.

    Uses Chain of Thought reasoning to create comprehensive outlines
    that follow children's picture book conventions.
    """

    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought(StoryOutlineSignature)
        self.generate_bibles = dspy.ChainOfThought(CharacterBibleSignature)
        self.select_style = dspy.ChainOfThought(IllustrationStyleSignature)

    def _parse_character_bibles(self, bibles_text: str) -> list[CharacterBible]:
        """Parse the raw character bibles text into structured CharacterBible objects."""
        bibles = []
        if not bibles_text:
            return bibles

        # Split by CHARACTER: markers
        sections = re.split(r'\n(?=CHARACTER:)', bibles_text.strip())

        for section in sections:
            if not section.strip():
                continue

            bible = CharacterBible(name="Unknown")

            for line in section.split('\n'):
                line = line.strip()
                if not line or ':' not in line:
                    continue

                key, value = line.split(':', 1)
                key = key.strip().upper()
                value = value.strip()

                if key == 'CHARACTER':
                    bible.name = value
                elif key == 'SPECIES':
                    bible.species = value
                elif key == 'AGE_APPEARANCE':
                    bible.age_appearance = value
                elif key == 'BODY':
                    bible.body = value
                elif key == 'FACE':
                    bible.face = value
                elif key == 'HAIR':
                    bible.hair = value
                elif key == 'EYES':
                    bible.eyes = value
                elif key == 'CLOTHING':
                    bible.clothing = value
                elif key == 'SIGNATURE_ITEM':
                    bible.signature_item = value
                elif key == 'COLOR_PALETTE':
                    bible.color_palette = [c.strip() for c in value.split(',')]
                elif key == 'STYLE_TAGS':
                    bible.style_tags = [t.strip() for t in value.split(',')]

            if bible.name != "Unknown":
                bibles.append(bible)

        return bibles

    def forward(self, goal: str, debug: bool = False) -> StoryOutline:
        """
        Generate a story outline from the given goal.

        Args:
            goal: The learning goal or theme for the story
            debug: If True, print debug info

        Returns:
            StoryOutline dataclass with all outline components
        """
        import sys

        result = self.generate(goal=goal)

        # Generate character bibles for illustration consistency
        bibles_result = self.generate_bibles(
            story_title=result.title,
            characters_description=result.characters,
            setting=result.setting,
        )
        character_bibles = self._parse_character_bibles(bibles_result.character_bibles)

        # Select illustration style based on story content
        style_result = self.select_style(
            story_title=result.title,
            story_summary=result.plot_summary,
            setting=result.setting,
            emotional_arc=result.emotional_arc,
            available_styles=get_all_styles_for_selection(),
        )

        # Parse the selected style
        selected_style_name = style_result.selected_style.strip().lower()
        illustration_style = get_style_by_name(selected_style_name)

        if debug:
            print(f"DEBUG Selected illustration style: {selected_style_name}", file=sys.stderr)
            print(f"DEBUG Style rationale: {style_result.style_rationale}", file=sys.stderr)

        outline = StoryOutline(
            title=result.title,
            protagonist_goal=result.protagonist_goal,
            stakes=result.stakes,
            characters=result.characters,
            setting=result.setting,
            emotional_arc=result.emotional_arc,
            plot_summary=result.plot_summary,
            spread_breakdown=result.spread_breakdown,
            moral=result.moral,
            goal=goal,
            character_bibles=character_bibles,
            illustration_style=illustration_style,
            style_rationale=style_result.style_rationale,
        )

        if debug:
            print(f"DEBUG Outline spread_breakdown:\n{result.spread_breakdown}", file=sys.stderr)
            print(f"DEBUG Parsed spreads: {outline.get_spreads()}", file=sys.stderr)
            print(f"DEBUG Character bibles: {len(character_bibles)} characters", file=sys.stderr)
            for cb in character_bibles:
                print(f"  - {cb.name}: {cb.to_prompt_string()[:100]}...", file=sys.stderr)

        return outline
