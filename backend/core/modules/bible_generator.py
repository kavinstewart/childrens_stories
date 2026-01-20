"""
DSPy Module for generating entity bibles from entity definitions.

Inline Entity Tagging workflow: after DirectStoryGenerator outputs entity
definitions, generate visual bibles for entities for illustration
consistency. Bibles are keyed by entity ID for direct lookup.

Robust Matching Strategy (story-8uvp):
1. Primary: Parse ENTITY_ID from LLM output (schema change)
2. Fallback: Deterministic matching (containment, token subset)
3. Validation: Ensure all entities have bibles
"""

import re
import dspy
from typing import Optional

from ..types import EntityBible, EntityDefinition
from ..signatures.entity_bible import EntityBibleSignature


class BibleGenerator(dspy.Module):
    """
    Generate entity visual bibles from entity definitions.

    Takes entity definitions from DirectStoryGenerator and generates
    detailed visual descriptions for entities. Bibles are keyed by
    entity ID for direct lookup during illustration.
    """

    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought(EntityBibleSignature)

    def _format_entity_definitions(self, entity_definitions: dict[str, EntityDefinition]) -> str:
        """Format entity definitions for the signature input.

        Includes entity IDs so the LLM can echo them back in output.
        """
        lines = []
        for entity_id, entity in entity_definitions.items():
            # Include entity_id so LLM can echo it back
            lines.append(f"{entity_id}: {entity.display_name} | DETAILS: {entity.brief_description}")
        return "\n".join(lines)

    def _parse_entity_bibles(self, bibles_text: str) -> list[EntityBible]:
        """Parse the raw entity bibles text into structured EntityBible objects.

        Handles both new format (with ENTITY_ID field) and legacy format.
        """
        bibles = []
        if not bibles_text:
            return bibles

        # Split by double newline (blank line) to separate bible sections
        # This keeps ENTITY_ID and CHARACTER together in the same section
        raw_sections = re.split(r'\n\s*\n', bibles_text.strip())

        for section in raw_sections:
            if not section.strip():
                continue

            bible = EntityBible(name="Unknown")
            current_entity_id = None

            for line in section.split('\n'):
                line = line.strip()
                if not line or ':' not in line:
                    continue

                key, value = line.split(':', 1)
                key = key.strip().upper()
                value = value.strip()

                if key == 'ENTITY_ID':
                    current_entity_id = value
                elif key == 'CHARACTER':
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

            # Attach entity_id if found
            if current_entity_id:
                bible.entity_id = current_entity_id

            if bible.name != "Unknown":
                bibles.append(bible)

        return bibles

    def _normalize_for_matching(self, s: str) -> str:
        """Normalize a string for matching: lowercase, strip, collapse whitespace."""
        return " ".join(s.lower().strip().split())

    def _strip_articles(self, s: str) -> str:
        """Remove leading articles (the, a, an) from a string."""
        normalized = s.lower().strip()
        for article in ("the ", "a ", "an "):
            if normalized.startswith(article):
                return normalized[len(article):].strip()
        return normalized

    def _deterministic_match(
        self,
        bible_name: str,
        entity_definitions: dict[str, EntityDefinition],
    ) -> Optional[str]:
        """Deterministic fallback matching using token-based strategies.

        Returns the matched entity_id or None if no match found.

        Matching strategies (in order of priority):
        1. Exact match (case-insensitive, with/without articles)
        2. Token subset: entity tokens are subset of bible tokens (word-based)
        3. Primary token match: first significant token matches

        We avoid substring containment as it causes false positives
        (e.g., "The River" matching "Otto the River Otter" via "river").
        """
        bible_norm = self._normalize_for_matching(bible_name)
        bible_stripped = self._strip_articles(bible_name)
        bible_tokens = set(bible_norm.split())
        bible_tokens_stripped = set(bible_stripped.split())

        candidates = []

        for entity_id, entity in entity_definitions.items():
            entity_norm = self._normalize_for_matching(entity.display_name)
            entity_stripped = self._strip_articles(entity.display_name)
            entity_tokens = set(entity_norm.split())
            entity_tokens_stripped = set(entity_stripped.split())

            # Strategy 1: Exact match (highest confidence)
            if bible_norm == entity_norm or bible_stripped == entity_stripped:
                return entity_id  # Immediate return for exact match

            # Strategy 2: Token subset (entity tokens all appear in bible tokens)
            # This handles "Otto" matching "Otto the River Otter"
            if entity_tokens_stripped and bible_tokens_stripped:
                if entity_tokens_stripped.issubset(bible_tokens_stripped):
                    # Score by how many tokens matched vs total bible tokens
                    # Prefer matches where entity covers more of the bible name
                    coverage = len(entity_tokens_stripped) / len(bible_tokens_stripped)
                    candidates.append((entity_id, "token_subset", coverage, len(entity_tokens_stripped)))
                elif bible_tokens_stripped.issubset(entity_tokens_stripped):
                    coverage = len(bible_tokens_stripped) / len(entity_tokens_stripped)
                    candidates.append((entity_id, "token_superset", coverage, len(bible_tokens_stripped)))

            # Strategy 3: Primary token match (first word matches)
            # This handles cases where the key identifier is at the start
            entity_first = entity_stripped.split()[0] if entity_stripped else ""
            bible_first = bible_stripped.split()[0] if bible_stripped else ""
            if entity_first and bible_first and entity_first == bible_first:
                candidates.append((entity_id, "first_token", 0.5, 1))

        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0][0]

        # Multiple candidates: prefer token_subset over token_superset,
        # higher coverage, and more tokens matched
        priority = {"token_subset": 1, "token_superset": 2, "first_token": 3}
        candidates.sort(key=lambda c: (priority.get(c[1], 99), -c[2], -c[3]))
        return candidates[0][0]

    def _match_bibles_to_entity_ids(
        self,
        bibles: list[EntityBible],
        entity_definitions: dict[str, EntityDefinition],
    ) -> dict[str, EntityBible]:
        """Match parsed bibles to entity IDs using layered strategy.

        Layer 1: Use entity_id from parsed bible (if present)
        Layer 2: Deterministic fallback (containment, token subset)

        Returns dict keyed by entity ID for direct lookup.
        """
        result = {}
        unmatched_bibles = []

        # Layer 1: Use entity_id if present in bible
        for bible in bibles:
            if bible.entity_id and bible.entity_id in entity_definitions:
                result[bible.entity_id] = bible
            else:
                unmatched_bibles.append(bible)

        # Layer 2: Deterministic fallback for bibles without entity_id
        # Track which entity_ids have been matched to avoid duplicates
        matched_entity_ids = set(result.keys())

        for bible in unmatched_bibles:
            # Filter out already-matched entity definitions
            remaining_definitions = {
                k: v for k, v in entity_definitions.items()
                if k not in matched_entity_ids
            }

            if not remaining_definitions:
                break

            entity_id = self._deterministic_match(bible.name, remaining_definitions)
            if entity_id:
                bible.entity_id = entity_id  # Store matched ID on bible
                result[entity_id] = bible
                matched_entity_ids.add(entity_id)

        return result

    def _validate_bible_completeness(
        self,
        bibles: dict[str, EntityBible],
        entity_definitions: dict[str, EntityDefinition],
    ) -> list[str]:
        """Validate that all entities have bibles.

        Returns list of missing entity IDs.
        """
        missing = []
        for entity_id in entity_definitions:
            if entity_id not in bibles:
                missing.append(entity_id)
        return missing

    def forward(
        self,
        title: str,
        story_text: str,
        entity_definitions: dict[str, EntityDefinition],
        debug: bool = False
    ) -> dict[str, EntityBible]:
        """
        Generate entity bibles from entity definitions.

        Args:
            title: The story title
            story_text: The complete story text for context
            entity_definitions: Dict of entity_id -> EntityDefinition from DirectStoryGenerator
            debug: If True, print debug info

        Returns:
            Dict of entity_id -> EntityBible
        """
        import sys

        if not entity_definitions:
            if debug:
                print("DEBUG No entities to generate bibles for", file=sys.stderr)
            return {}

        if debug:
            print(f"DEBUG Generating bibles for {len(entity_definitions)} entities", file=sys.stderr)

        formatted_entities = self._format_entity_definitions(entity_definitions)

        result = self.generate(
            story_title=title,
            story_text=story_text,
            extracted_entities=formatted_entities,
        )

        bibles = self._parse_entity_bibles(result.entity_bibles)

        if debug:
            print(f"DEBUG Parsed {len(bibles)} bibles from LLM output", file=sys.stderr)
            for b in bibles:
                print(f"  - {b.entity_id or '(no id)'}: {b.name}", file=sys.stderr)

        # Match bibles to entity IDs (layered strategy)
        entity_bibles = self._match_bibles_to_entity_ids(bibles, entity_definitions)

        # Validate completeness
        missing = self._validate_bible_completeness(entity_bibles, entity_definitions)
        if missing and debug:
            print(f"WARNING: Missing bibles for entities: {missing}", file=sys.stderr)

        if debug:
            print(f"DEBUG Generated {len(entity_bibles)} entity bibles:", file=sys.stderr)
            for entity_id, bible in entity_bibles.items():
                print(f"  - {entity_id}: {bible.name} - {bible.to_prompt_string()[:50]}...", file=sys.stderr)

        return entity_bibles
