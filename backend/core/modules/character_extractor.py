"""
DEPRECATED: CharacterExtractor is no longer used in the main story generation pipeline.

This module has been replaced by inline entity tagging in DirectStoryGenerator.
Entities (@e1, @e2, etc.) are now defined at story generation time, eliminating
the need to extract characters afterward.

This module is kept for backwards compatibility with:
- Existing tests that verify alias extraction
- Legacy code paths during the transition period
- Migration script that may need to process old stories

It will be removed in a future version after migration is complete.
"""

import re
import dspy
import warnings
from dataclasses import dataclass

from ..signatures.character_extractor import CharacterExtractorSignature


@dataclass
class ExtractedCharacter:
    """A character extracted from a story."""
    name: str
    details: str  # Everything the story tells us about them
    aliases: list[str] = None  # Alternative names/references for this character

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


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

            # Parse "NAME: [name] | ALIASES: [aliases] | DETAILS: [details]" format
            match_with_aliases = re.match(
                r'NAME:\s*(.+?)\s*\|\s*ALIASES:\s*(.+?)\s*\|\s*DETAILS:\s*(.+)',
                line,
                re.IGNORECASE
            )
            if match_with_aliases:
                name = match_with_aliases.group(1).strip()
                aliases_str = match_with_aliases.group(2).strip()
                details = match_with_aliases.group(3).strip()
                # Parse comma-separated aliases, handling "none" case
                if aliases_str.lower() == 'none':
                    aliases = []
                else:
                    aliases = [a.strip() for a in aliases_str.split(',') if a.strip()]
                characters.append(ExtractedCharacter(name=name, details=details, aliases=aliases))
                continue

            # Parse "NAME: [name] | DETAILS: [details]" format (no aliases)
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
