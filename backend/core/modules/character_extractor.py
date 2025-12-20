"""
DSPy Module for extracting characters from a completed story.

Story-first workflow: after the story is written, extract what characters
appeared so we can generate visual bibles for illustration consistency.
"""

import re
import dspy
from dataclasses import dataclass

from ..signatures.character_extractor import CharacterExtractorSignature


@dataclass
class ExtractedCharacter:
    """A character extracted from a story."""
    name: str
    details: str  # Everything the story tells us about them

    def to_bible_input(self) -> str:
        """Format for character bible generation."""
        return f"{self.name}: {self.details}"


class CharacterExtractor(dspy.Module):
    """
    Extract characters from a completed story.

    Takes the story text and identifies all named characters along
    with their descriptions. This is used to generate character
    bibles for illustration consistency.
    """

    def __init__(self):
        super().__init__()
        self.extract = dspy.ChainOfThought(CharacterExtractorSignature)

    def _parse_characters(self, raw_output: str) -> list[ExtractedCharacter]:
        """Parse the raw output into ExtractedCharacter objects."""
        characters = []

        for line in raw_output.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

            # Parse "NAME: [name] | DETAILS: [details]" format
            match = re.match(
                r'NAME:\s*(.+?)\s*\|\s*DETAILS:\s*(.+)',
                line,
                re.IGNORECASE
            )
            if match:
                name = match.group(1).strip()
                details = match.group(2).strip()
                characters.append(ExtractedCharacter(name=name, details=details))
            else:
                # Try alternate format without pipe
                alt_match = re.match(r'NAME:\s*(.+?)(?:\s*[-:]\s*|\s+)DETAILS:\s*(.+)', line, re.IGNORECASE)
                if alt_match:
                    name = alt_match.group(1).strip()
                    details = alt_match.group(2).strip()
                    characters.append(ExtractedCharacter(name=name, details=details))

        return characters

    def forward(
        self,
        title: str,
        story_text: str,
        debug: bool = False
    ) -> list[ExtractedCharacter]:
        """
        Extract characters from the story.

        Args:
            title: The story title
            story_text: The complete story text (all spreads concatenated)
            debug: If True, print debug info

        Returns:
            List of ExtractedCharacter objects
        """
        import sys

        if debug:
            print(f"DEBUG Extracting characters from: {title}", file=sys.stderr)

        result = self.extract(
            story_title=title,
            story_text=story_text,
        )

        characters = self._parse_characters(result.characters)

        if debug:
            print(f"DEBUG Extracted {len(characters)} characters:", file=sys.stderr)
            for char in characters:
                print(f"  - {char.name}: {char.details[:50]}...", file=sys.stderr)

        return characters
