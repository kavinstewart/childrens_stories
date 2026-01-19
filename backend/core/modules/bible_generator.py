"""
DSPy Module for generating character bibles from extracted characters.

Story-first workflow: after extracting characters from the completed story,
generate visual bibles for illustration consistency.
"""

import re
import dspy

from ..types import CharacterBible
from ..signatures.character_bible import CharacterBibleSignature
from .character_extractor import ExtractedCharacter


class BibleGenerator(dspy.Module):
    """
    Generate character visual bibles from extracted characters.

    Takes characters extracted from a completed story and generates
    detailed visual descriptions for illustration consistency.
    """

    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought(CharacterBibleSignature)

    def _format_extracted_characters(self, characters: list[ExtractedCharacter]) -> str:
        """Format extracted characters for the signature input."""
        lines = []
        for char in characters:
            lines.append(f"NAME: {char.name} | DETAILS: {char.details}")
        return "\n".join(lines)

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

    def forward(
        self,
        title: str,
        story_text: str,
        extracted_characters: list[ExtractedCharacter],
        debug: bool = False
    ) -> list[CharacterBible]:
        """
        Generate character bibles from extracted characters.

        Args:
            title: The story title
            story_text: The complete story text for context
            extracted_characters: Characters extracted from the story
            debug: If True, print debug info

        Returns:
            List of CharacterBible objects
        """
        import sys

        if not extracted_characters:
            if debug:
                print("DEBUG No characters to generate bibles for", file=sys.stderr)
            return []

        if debug:
            print(f"DEBUG Generating bibles for {len(extracted_characters)} characters", file=sys.stderr)

        formatted_characters = self._format_extracted_characters(extracted_characters)

        result = self.generate(
            story_title=title,
            story_text=story_text,
            extracted_characters=formatted_characters,
        )

        bibles = self._parse_character_bibles(result.character_bibles)

        if debug:
            print(f"DEBUG Generated {len(bibles)} character bibles:", file=sys.stderr)
            for bible in bibles:
                print(f"  - {bible.name}: {bible.to_prompt_string()[:50]}...", file=sys.stderr)

        return bibles
