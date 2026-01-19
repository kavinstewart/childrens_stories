"""
DSPy Module for generating character bibles from entity definitions.

Inline Entity Tagging workflow: after DirectStoryGenerator outputs entity
definitions, generate visual bibles for character entities for illustration
consistency. Bibles are keyed by entity ID for direct lookup.
"""

import re
import dspy
from typing import Optional

from ..types import CharacterBible, EntityDefinition
from ..signatures.character_bible import CharacterBibleSignature


class BibleGenerator(dspy.Module):
    """
    Generate character visual bibles from entity definitions.

    Takes entity definitions from DirectStoryGenerator and generates
    detailed visual descriptions for character entities. Bibles are
    keyed by entity ID for direct lookup during illustration.
    """

    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought(CharacterBibleSignature)

    def _format_entity_definitions(self, entity_definitions: dict[str, EntityDefinition]) -> str:
        """Format entity definitions for the signature input.

        Only includes character-type entities.
        """
        lines = []
        for entity_id, entity in entity_definitions.items():
            if entity.is_character:
                lines.append(f"NAME: {entity.display_name} | DETAILS: {entity.brief_description}")
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

    def _match_bibles_to_entity_ids(
        self,
        bibles: list[CharacterBible],
        entity_definitions: dict[str, EntityDefinition],
    ) -> dict[str, CharacterBible]:
        """Match parsed bibles to entity IDs by display name.

        Returns dict keyed by entity ID for direct lookup.
        """
        result = {}

        # Build lookup from display name -> entity_id
        name_to_entity_id = {}
        for entity_id, entity in entity_definitions.items():
            if entity.is_character:
                # Normalize for matching
                name_to_entity_id[entity.display_name.lower().strip()] = entity_id

        for bible in bibles:
            bible_name_lower = bible.name.lower().strip()
            if bible_name_lower in name_to_entity_id:
                entity_id = name_to_entity_id[bible_name_lower]
                result[entity_id] = bible

        return result

    def forward(
        self,
        title: str,
        story_text: str,
        entity_definitions: dict[str, EntityDefinition],
        debug: bool = False
    ) -> dict[str, CharacterBible]:
        """
        Generate character bibles from entity definitions.

        Args:
            title: The story title
            story_text: The complete story text for context
            entity_definitions: Dict of entity_id -> EntityDefinition from DirectStoryGenerator
            debug: If True, print debug info

        Returns:
            Dict of entity_id -> CharacterBible (only character entities)
        """
        import sys

        # Filter to only character entities
        character_entities = {
            eid: entity for eid, entity in entity_definitions.items()
            if entity.is_character
        }

        if not character_entities:
            if debug:
                print("DEBUG No character entities to generate bibles for", file=sys.stderr)
            return {}

        if debug:
            print(f"DEBUG Generating bibles for {len(character_entities)} character entities", file=sys.stderr)

        formatted_characters = self._format_entity_definitions(character_entities)

        result = self.generate(
            story_title=title,
            story_text=story_text,
            extracted_characters=formatted_characters,
        )

        bibles = self._parse_character_bibles(result.character_bibles)

        # Match bibles to entity IDs
        entity_bibles = self._match_bibles_to_entity_ids(bibles, character_entities)

        if debug:
            print(f"DEBUG Generated {len(entity_bibles)} character bibles:", file=sys.stderr)
            for entity_id, bible in entity_bibles.items():
                print(f"  - {entity_id}: {bible.name} - {bible.to_prompt_string()[:50]}...", file=sys.stderr)

        return entity_bibles
