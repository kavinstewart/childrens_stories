"""
DSPy Module for generating stories directly from a goal.

Story-first workflow: generate the complete story in one shot,
then extract characters afterward. This replaces the outline-first
approach which invented characters before the story existed.

Inline Entity Tagging:
Stories now include an [Entities] block at the top that defines all entities
with stable IDs (@e1, @e2, etc.). Spreads use these IDs in [Characters: @e1, @e2]
instead of character names, eliminating the need for fuzzy name matching.
"""

import re
import dspy

from ..types import StorySpread, EntityDefinition
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

    def _parse_characters_field(self, characters_str: str, has_entities: bool = False) -> tuple[list[str] | None, list[str] | None]:
        """
        Parse the [Characters: ...] field into entity IDs or character names.

        Args:
            characters_str: Raw string from [Characters: ...] field
            has_entities: Whether the story has an [Entities] block (use entity IDs)

        Returns:
            Tuple of (present_entity_ids, present_characters):
            - If using entity IDs: (["@e1", "@e2"], None)
            - If using legacy names: (None, ["George", "Owl"])
            - If "none" or empty: ([], None) for entity mode, (None, []) for legacy
        """
        if not characters_str:
            return (None, None)

        characters_str = characters_str.strip()

        # Handle explicit "none" or empty
        if characters_str.lower() in ("none", "n/a", "no one", "nobody", "empty", ""):
            if has_entities:
                return ([], None)  # Empty entity list
            else:
                return (None, [])  # Empty legacy list

        # Split by comma and clean up
        items = [item.strip() for item in characters_str.split(",")]
        items = [item for item in items if item and item.lower() not in ("none", "n/a")]

        if not items:
            if has_entities:
                return ([], None)
            else:
                return (None, [])

        # Separate entity IDs (@eN) from legacy names
        entity_ids = [item for item in items if item.startswith("@")]
        names = [item for item in items if not item.startswith("@")]

        if has_entities and entity_ids:
            # New format with entity IDs
            return (entity_ids, None)
        elif names:
            # Legacy format with character names
            return (None, names)
        elif entity_ids and not has_entities:
            # Entity IDs without [Entities] block - treat as entity IDs anyway
            return (entity_ids, None)
        else:
            return (None, None)

    def _parse_entities_block(self, raw_output: str) -> tuple[str, dict[str, EntityDefinition]]:
        """
        Parse the [Entities] block from story output.

        Format:
        [Entities]
        @e1: George Washington (character, young boy exploring the forest)
        @e2: The Wise Owl (character, elderly owl who gives advice)
        @e3: The Enchanted Forest (location, misty magical woods)

        Args:
            raw_output: Full story output text

        Returns:
            Tuple of (remaining_output, entity_definitions dict)
        """
        entity_definitions = {}

        # Look for [Entities] block
        entities_match = re.search(
            r'\[Entities\]\s*(.*?)(?=\n\s*(?:TITLE:|Spread\s+\d+:))',
            raw_output,
            re.DOTALL | re.IGNORECASE
        )

        if not entities_match:
            # No entities block - return original output
            return raw_output, {}

        entities_block = entities_match.group(1).strip()
        remaining_output = raw_output[entities_match.end():]

        # Parse each entity line: @e1: Display Name (description)
        for line in entities_block.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Match: @e1: Display Name (description)
            entity_match = re.match(
                r'(@e\d+):\s*(.+?)\s*\((.+?)\)\s*$',
                line
            )
            if entity_match:
                entity_id = entity_match.group(1)
                display_name = entity_match.group(2).strip()
                brief_description = entity_match.group(3).strip()

                entity_definitions[entity_id] = EntityDefinition(
                    entity_id=entity_id,
                    display_name=display_name,
                    entity_type="entity",  # Default type for all entities
                    brief_description=brief_description,
                )

        return remaining_output, entity_definitions

    def _parse_story_output(self, raw_output: str) -> tuple[str, list[StorySpread], dict[str, EntityDefinition]]:
        """
        Parse the raw LLM output into title, spreads, and entity definitions.

        Validates that [Characters:] field is present for each spread.
        Emits warnings for missing fields but continues with None (fallback path).

        Returns:
            Tuple of (title, list of StorySpread objects, entity_definitions dict)
        """
        import sys

        # First, parse [Entities] block if present
        remaining_output, entity_definitions = self._parse_entities_block(raw_output)
        has_entities = len(entity_definitions) > 0

        # Extract title
        title_match = re.search(r'TITLE:\s*(.+?)(?:\n|$)', remaining_output, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else "Untitled Story"

        # Parse spreads
        spreads = []
        missing_characters_spreads = []  # Track spreads missing [Characters:] field

        # Split by "Spread N:" markers
        parts = re.split(r'(?=Spread\s+\d+:)', remaining_output, flags=re.IGNORECASE)

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
            present_entity_ids = None
            present_characters = None
            chars_match = re.search(r'\[Characters:\s*(.+?)\]', content, re.DOTALL)
            if chars_match:
                present_entity_ids, present_characters = self._parse_characters_field(
                    chars_match.group(1), has_entities=has_entities
                )
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
                present_entity_ids=present_entity_ids,
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

        return title, spreads, entity_definitions

    def forward(self, goal: str, debug: bool = False) -> tuple[str, list[StorySpread], dict[str, EntityDefinition]]:
        """
        Generate a complete story from the given goal.

        Args:
            goal: The theme, concept, or learning goal for the story
            debug: If True, print debug info

        Returns:
            Tuple of (title, list of StorySpread objects, entity_definitions dict)
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
        title, spreads, entity_definitions = self._parse_story_output(result.story)

        if debug:
            print(f"DEBUG Generated: '{title}' with {len(spreads)} spreads", file=sys.stderr)
            total_words = sum(s.word_count for s in spreads)
            print(f"DEBUG Total word count: {total_words}", file=sys.stderr)
            if entity_definitions:
                print(f"DEBUG Extracted {len(entity_definitions)} entities: {list(entity_definitions.keys())}", file=sys.stderr)

        # Validate we got 12 spreads
        if len(spreads) != 12:
            print(f"WARNING: Expected 12 spreads, got {len(spreads)}", file=sys.stderr)

        return title, spreads, entity_definitions
