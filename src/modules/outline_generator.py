"""
DSPy Module for generating story outlines.
"""

import dspy
import re
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from ..signatures.story_outline import StoryOutlineSignature
from ..signatures.character_bible import CharacterBibleSignature
from ..signatures.illustration_style import IllustrationStyleSignature
from .illustration_styles import (
    IllustrationStyleType,
    StyleDefinition,
    get_style_by_name,
    get_all_styles_for_selection,
    ILLUSTRATION_STYLES,
)


@dataclass
class CharacterBible:
    """Visual definition for a single character."""

    name: str
    species: str = ""
    age_appearance: str = ""
    body: str = ""
    face: str = ""
    hair: str = ""
    eyes: str = ""
    clothing: str = ""
    signature_item: str = ""
    color_palette: list[str] = field(default_factory=list)
    style_tags: list[str] = field(default_factory=list)

    def to_prompt_string(self) -> str:
        """Convert to a string suitable for image generation prompts."""
        parts = [f"{self.name}:"]
        if self.species:
            parts.append(f"a {self.age_appearance} {self.species}" if self.age_appearance else self.species)
        if self.body:
            parts.append(self.body)
        if self.face:
            parts.append(f"face: {self.face}")
        if self.hair:
            parts.append(f"hair: {self.hair}")
        if self.eyes:
            parts.append(f"eyes: {self.eyes}")
        if self.clothing:
            parts.append(f"wearing {self.clothing}")
        if self.signature_item:
            parts.append(f"with {self.signature_item}")
        return ", ".join(parts)


@dataclass
class StoryOutline:
    """Structured representation of a story outline."""

    title: str
    protagonist_goal: str
    stakes: str
    characters: str
    setting: str
    emotional_arc: str
    plot_summary: str
    page_breakdown: str
    moral: str
    goal: str  # Original goal for reference
    character_bibles: list[CharacterBible] = field(default_factory=list)
    illustration_style: Optional[StyleDefinition] = None
    style_rationale: str = ""

    def get_pages(self) -> list[dict]:
        """Parse page_breakdown into structured list."""
        import re
        pages = []
        if not self.page_breakdown:
            return pages
        for line in self.page_breakdown.split("\n"):
            line = line.strip()
            # Remove markdown formatting like *Page 1* or **Page 1**
            clean_line = re.sub(r"^\*+", "", line).strip()
            clean_line = re.sub(r"\*+$", "", clean_line.split(":")[0] if ":" in clean_line else clean_line).strip()

            if clean_line.lower().startswith("page"):
                # Try to extract page number and content
                parts = line.split(":", 1)
                if len(parts) == 2:
                    # Clean up the page identifier too
                    page_num = re.sub(r"[\*_]", "", parts[0]).strip()
                    content = parts[1].strip()
                    pages.append({"page": page_num, "content": content})
        return pages

    @property
    def page_count(self) -> int:
        """Return the number of pages in the outline."""
        return len(self.get_pages())

    def get_character_bible(self, name: str) -> Optional[CharacterBible]:
        """Find a character bible by name (case-insensitive partial match)."""
        name_lower = name.lower()
        for bible in self.character_bibles:
            if name_lower in bible.name.lower():
                return bible
        return None

    def get_all_style_tags(self) -> list[str]:
        """Get unified style tags from all characters."""
        all_tags = set()
        for bible in self.character_bibles:
            all_tags.update(bible.style_tags)
        return list(all_tags)


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
            page_breakdown=result.page_breakdown,
            moral=result.moral,
            goal=goal,
            character_bibles=character_bibles,
            illustration_style=illustration_style,
            style_rationale=style_result.style_rationale,
        )

        if debug:
            print(f"DEBUG Outline page_breakdown:\n{result.page_breakdown}", file=sys.stderr)
            print(f"DEBUG Parsed pages: {outline.get_pages()}", file=sys.stderr)
            print(f"DEBUG Character bibles: {len(character_bibles)} characters", file=sys.stderr)
            for cb in character_bibles:
                print(f"  - {cb.name}: {cb.to_prompt_string()[:100]}...", file=sys.stderr)

        return outline
