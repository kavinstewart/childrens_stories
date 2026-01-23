"""
Centralized domain types for the Children's Story Generator.

All dataclasses that are used across multiple modules are defined here
to make data flow explicit and avoid circular imports.
"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
import json
import re
from io import BytesIO


# =============================================================================
# Entity Definition Types (Inline Entity Tagging System)
# =============================================================================


@dataclass
class EntityDefinition:
    """
    Definition of an entity extracted from story generation.

    Entity IDs (e.g., @e1, @e2) provide stable, unambiguous references
    to characters, locations, and other entities throughout a story.
    """

    entity_id: str  # e.g., "@e1", "@e2"
    display_name: str  # e.g., "George Washington", "The Wise Owl"
    entity_type: str  # "character", "location", "object", etc.
    brief_description: str  # Brief context from story generation

    @property
    def is_character(self) -> bool:
        """Check if this entity is a character."""
        return self.entity_type == "character"

    def __eq__(self, other):
        if not isinstance(other, EntityDefinition):
            return False
        return (
            self.entity_id == other.entity_id
            and self.display_name == other.display_name
            and self.entity_type == other.entity_type
            and self.brief_description == other.brief_description
        )


# =============================================================================
# Character Name Matching Helpers
# =============================================================================

def _normalize_name(s: str) -> str:
    """Normalize a string for matching: lowercase, strip, collapse whitespace."""
    return " ".join(s.lower().strip().split())


def _strip_leading_article(s: str) -> str:
    """Remove leading 'the ', 'a ', 'an ' from a string."""
    normalized = s.lower().strip()
    for article in ("the ", "a ", "an "):
        if normalized.startswith(article):
            return normalized[len(article):].strip()
    return normalized


def _names_match(query: str, canonical: str, aliases: list[str] = None) -> bool:
    """
    Check if query matches canonical name using normalization and article-stripping.

    Supports exact match and article-stripped match (e.g., "Blue Bird" matches "The Blue Bird").
    Also checks against provided aliases for flexible matching.
    Does NOT use substring matching to avoid false positives.

    Args:
        query: The name to search for
        canonical: The canonical character name
        aliases: Optional list of alias names that should also match

    Returns:
        True if query matches canonical name or any alias
    """
    query_norm = _normalize_name(query)
    canonical_norm = _normalize_name(canonical)

    # Exact match (normalized)
    if query_norm == canonical_norm:
        return True

    # Article-stripped match (both directions)
    query_stripped = _strip_leading_article(query)
    canonical_stripped = _strip_leading_article(canonical)

    if query_stripped == canonical_stripped:
        return True
    if query_norm == canonical_stripped:
        return True
    if query_stripped == canonical_norm:
        return True

    # Check against aliases
    if aliases:
        for alias in aliases:
            alias_norm = _normalize_name(alias)
            alias_stripped = _strip_leading_article(alias)

            # Check various matching combinations with alias
            if query_norm == alias_norm:
                return True
            if query_stripped == alias_stripped:
                return True
            if query_norm == alias_stripped:
                return True
            if query_stripped == alias_norm:
                return True

    return False


def build_entity_lookup(entity_bibles: list) -> dict[str, str]:
    """
    Build a lookup dict mapping normalized names (and variants) to canonical names.

    Includes both canonical names and aliases for flexible lookup.

    Args:
        entity_bibles: List of EntityBible objects

    Returns:
        Dict mapping normalized name variants -> canonical entity name
    """
    lookup = {}
    for bible in entity_bibles:
        canonical = bible.name
        # Add normalized canonical name
        normalized = _normalize_name(canonical)
        lookup[normalized] = canonical
        # Add article-stripped variant
        stripped = _strip_leading_article(canonical)
        if stripped != normalized:
            lookup[stripped] = canonical

        # Add aliases if present
        aliases = getattr(bible, 'aliases', []) or []
        for alias in aliases:
            alias_norm = _normalize_name(alias)
            if alias_norm not in lookup:
                lookup[alias_norm] = canonical
            alias_stripped = _strip_leading_article(alias)
            if alias_stripped != alias_norm and alias_stripped not in lookup:
                lookup[alias_stripped] = canonical

    return lookup


def name_matches_in_text(character_name: str, text: str) -> bool:
    """
    Check if a character name (or article-stripped variant) appears as whole word(s) in text.

    Uses word-boundary regex matching to avoid false positives like "He" matching "The".
    For multi-word names, matches the whole phrase as a unit.

    Args:
        character_name: The canonical character name (e.g., "The Blue Bird")
        text: The text to search in

    Returns:
        True if the name appears as whole word(s), False otherwise
    """
    text_lower = text.lower()
    name_normalized = _normalize_name(character_name)

    # Try matching the full name with word boundaries
    # \b ensures we match whole words only
    pattern = r'\b' + re.escape(name_normalized) + r'\b'
    if re.search(pattern, text_lower):
        return True

    # Try matching article-stripped version (e.g., "Blue Bird" for "The Blue Bird")
    name_stripped = _strip_leading_article(character_name)
    if name_stripped != name_normalized:
        pattern_stripped = r'\b' + re.escape(name_stripped) + r'\b'
        if re.search(pattern_stripped, text_lower):
            return True

    return False


# Conditional import for PIL (only needed at runtime for some methods)
if TYPE_CHECKING:
    from PIL import Image


# =============================================================================
# Style Types
# =============================================================================


@dataclass
class StyleDefinition:
    """Complete definition of an illustration style for Nano Banana Pro."""

    name: str
    description: str  # Human-readable description for LLM selection
    prompt_prefix: str  # Concise style direction (1-2 sentences)
    best_for: list[str]  # Story types this style works well for
    lighting_direction: str = ""  # Specific lighting for this style


# Default style values when no style is provided
DEFAULT_STYLE_PREFIX = "Warm, inviting children's book illustration in soft watercolor and gouache style"
DEFAULT_LIGHTING = "soft diffused natural light with gentle shadows"


def build_illustration_prompt(
    illustration_prompt: str,
    style_prefix: str,
    lighting: str,
) -> str:
    """
    Build the composed prompt for image generation.

    This is the single source of truth for illustration prompt composition.
    Used by both SpreadIllustrator (generation) and StoryRepository (API responses).

    Args:
        illustration_prompt: Scene description for this spread
        style_prefix: Style direction (e.g., "Warm watercolor style")
        lighting: Lighting direction (e.g., "soft diffused natural light")

    Returns:
        Complete prompt string for image generation
    """
    return f"""{style_prefix}, 16:9 aspect ratio in landscape format.

Scene: {illustration_prompt}

Lighting: {lighting}.

Wide shot framing with space at bottom for text overlay.

CRITICAL: Any named character in this scene MUST match their reference image EXACTLY - same face, same age, same hair color, same clothing. Do not create different-looking versions of characters. If a character reference image was provided above, use it as the definitive appearance."""


# =============================================================================
# Character Types
# =============================================================================


@dataclass
class EntityBible:
    """Visual definition for a single entity (character, location, or object)."""

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
    aliases: list[str] = field(default_factory=list)  # Alternative names for this character
    entity_id: Optional[str] = None  # Entity ID from LLM output (e.g., "@e1")

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

    def to_dict(self) -> dict:
        """Convert to dict for JSON storage in database."""
        return {
            "name": self.name,
            "species": self.species,
            "age_appearance": self.age_appearance,
            "body": self.body,
            "face": self.face,
            "hair": self.hair,
            "eyes": self.eyes,
            "clothing": self.clothing,
            "signature_item": self.signature_item,
            "color_palette": self.color_palette,
            "style_tags": self.style_tags,
            "aliases": self.aliases,
            "entity_id": self.entity_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EntityBible":
        """Reconstruct from stored dict data."""
        return cls(
            name=data.get("name", ""),
            species=data.get("species", ""),
            age_appearance=data.get("age_appearance", ""),
            body=data.get("body", ""),
            face=data.get("face", ""),
            hair=data.get("hair", ""),
            eyes=data.get("eyes", ""),
            clothing=data.get("clothing", ""),
            signature_item=data.get("signature_item", ""),
            color_palette=data.get("color_palette", []),
            style_tags=data.get("style_tags", []),
            aliases=data.get("aliases", []),
            entity_id=data.get("entity_id"),
        )


@dataclass
class CharacterReferenceSheet:
    """Generated reference image for a character."""

    character_name: str
    reference_image: bytes  # PNG/JPEG bytes of the reference portrait
    prompt_used: str = ""
    character_description: str = ""  # Age, physical features, etc. from character bible
    bible: Optional["EntityBible"] = None  # Full entity bible for editing
    entity_id: Optional[str] = None  # Entity ID for new stories (e.g., "@e1")

    def to_pil_image(self) -> "Image.Image":
        """Convert to PIL Image for passing to Nano Banana Pro."""
        from PIL import Image
        return Image.open(BytesIO(self.reference_image))


@dataclass
class StoryReferenceSheets:
    """All reference sheets for a story.

    For new stories with entity tagging, character_sheets is keyed by entity ID (e.g., "@e1").
    For legacy stories, it's keyed by character name.
    """

    story_title: str
    character_sheets: dict[str, CharacterReferenceSheet] = field(default_factory=dict)

    def get_sheet(self, entity_id_or_name: str) -> Optional[CharacterReferenceSheet]:
        """Get reference sheet by entity ID or character name.

        For new stories: direct dict lookup by entity ID (e.g., "@e1").
        For legacy stories: name-based matching with aliases.

        Args:
            entity_id_or_name: Entity ID (e.g., "@e1") or character name

        Returns:
            CharacterReferenceSheet if found, None otherwise
        """
        # First, try direct lookup (works for both entity IDs and exact name matches)
        if entity_id_or_name in self.character_sheets:
            return self.character_sheets[entity_id_or_name]

        # Fall back to name-based matching for legacy stories (non-@ keys)
        # Only do this if the query is not an entity ID
        if not entity_id_or_name.startswith("@"):
            for key, sheet in self.character_sheets.items():
                # Skip entity ID keys - they use direct lookup only
                if key.startswith("@"):
                    continue
                # Get aliases from the bible attached to this sheet
                aliases = getattr(sheet.bible, 'aliases', []) if sheet.bible else []
                if _names_match(entity_id_or_name, key, aliases=aliases):
                    return sheet

        return None

    def get_all_pil_images(self) -> list[tuple[str, "Image.Image"]]:
        """Get all reference images as PIL Images with their names."""
        return [
            (name, sheet.to_pil_image())
            for name, sheet in self.character_sheets.items()
        ]

    def get_all_with_descriptions(self) -> list[tuple[str, "Image.Image", str]]:
        """Get all reference images with names and descriptions for QA."""
        return [
            (name, sheet.to_pil_image(), sheet.character_description)
            for name, sheet in self.character_sheets.items()
        ]


# =============================================================================
# Story Structure Types
# =============================================================================


@dataclass
class StoryMetadata:
    """Metadata for story illustration: style and entities.

    This is NOT an outline - the story-first workflow generates the complete
    story directly. This container holds metadata needed for illustration:
    - Entity visual descriptions (bibles) for consistent illustration
    - Selected illustration style
    - Title for reference

    For new stories using entity tagging:
    - entity_definitions: map of entity ID -> EntityDefinition (all entities)
    - entity_bibles: map of entity ID -> EntityBible (all entities with bibles)
    """

    title: str
    # DEPRECATED: Use entity_bibles instead for new stories
    character_bibles: list[EntityBible] = field(default_factory=list)
    illustration_style: Optional[StyleDefinition] = None
    style_rationale: str = ""
    # New entity tagging fields (entity ID -> definition)
    entity_definitions: dict[str, "EntityDefinition"] = field(default_factory=dict)
    entity_bibles: dict[str, EntityBible] = field(default_factory=dict)

    def get_entity_bible(self, name_or_entity_id: str) -> Optional[EntityBible]:
        """Find an entity bible by entity ID or name.

        For new stories with entity tagging: looks up by entity ID (e.g., "@e1").
        For legacy stories: uses name-based matching with aliases.

        Args:
            name_or_entity_id: Entity ID (e.g., "@e1") or entity name

        Returns:
            EntityBible if found, None otherwise
        """
        # First, try entity ID lookup (new system)
        if name_or_entity_id.startswith("@") and name_or_entity_id in self.entity_bibles:
            return self.entity_bibles[name_or_entity_id]

        # Fall back to name-based lookup for legacy stories
        for bible in self.character_bibles:
            if _names_match(name_or_entity_id, bible.name, aliases=bible.aliases):
                return bible
        return None

    # Backwards-compatible alias (deprecated)
    def get_character_bible(self, name_or_entity_id: str) -> Optional[EntityBible]:
        """Deprecated: Use get_entity_bible instead."""
        return self.get_entity_bible(name_or_entity_id)


@dataclass
class StorySpread:
    """Structured representation of a single story spread (two facing pages).

    A spread is a double-page unit in a picture book. Standard picture books
    have 12 spreads for story content, with 35-50 words per spread.
    """

    spread_number: int
    text: str
    word_count: int
    page_turn_note: str = ""  # What makes reader want to turn the page
    illustration_prompt: str = ""
    illustration_image: Optional[bytes] = None  # Generated illustration for this spread
    was_revised: bool = False  # Backwards compatibility
    # Characters visually present in this spread's illustration (explicit from LLM)
    # DEPRECATED: Use present_entity_ids instead
    present_characters: Optional[list[str]] = None
    # Entity IDs visually present in this spread's illustration (e.g., ["@e1", "@e2"])
    # Required for illustration with entity tagging system
    present_entity_ids: Optional[list[str]] = None

    @classmethod
    def from_db_record(cls, record: dict) -> "StorySpread":
        """Construct a StorySpread from a database record.

        This is the single source of truth for DB -> domain mapping.
        Used by both story_generation.py (save) and spread_regeneration.py (load).

        Args:
            record: Dict-like database record (asyncpg.Record or dict)

        Returns:
            StorySpread instance with all fields populated from record
        """
        # Parse present_entity_ids - asyncpg returns JSONB as string
        present_entity_ids = record.get("present_entity_ids")
        if isinstance(present_entity_ids, str):
            present_entity_ids = json.loads(present_entity_ids)

        return cls(
            spread_number=record["spread_number"],
            text=record["text"],
            word_count=record.get("word_count", 0) or 0,
            was_revised=record.get("was_revised", False) or False,
            page_turn_note=record.get("page_turn_note", "") or "",
            illustration_prompt=record.get("illustration_prompt", "") or "",
            present_entity_ids=present_entity_ids,
        )

    @property
    def page_number(self) -> int:
        """Alias for spread_number (backwards compatibility)."""
        return self.spread_number

    def __str__(self) -> str:
        return f"Spread {self.spread_number}: {self.text}"


# =============================================================================
# Complete Story Types
# =============================================================================


@dataclass
class GeneratedStory:
    """Complete generated story with all metadata."""

    title: str
    goal: str
    metadata: StoryMetadata
    spreads: list[StorySpread]
    reference_sheets: Optional[StoryReferenceSheets] = None
    is_illustrated: bool = False

    @property
    def word_count(self) -> int:
        """Total word count of the story."""
        return sum(spread.word_count for spread in self.spreads)

    @property
    def spread_count(self) -> int:
        """Number of spreads in the story."""
        return len(self.spreads)

    # Backwards compatibility
    @property
    def pages(self) -> list[StorySpread]:
        """Alias for spreads (backwards compatibility)."""
        return self.spreads

    @property
    def page_count(self) -> int:
        """Alias for spread_count (backwards compatibility)."""
        return self.spread_count

    def to_formatted_string(self, include_illustration_prompts: bool = False) -> str:
        """Format the story for display/output."""
        lines = [
            f"# {self.title}",
            "",
            f"*A story about: {self.goal}*",
            "",
            "---",
            "",
        ]

        for spread in self.spreads:
            lines.append(f"**Spread {spread.spread_number}**")
            lines.append("")
            lines.append(spread.text)

            if include_illustration_prompts and spread.illustration_prompt:
                lines.append("")
                lines.append(f"*[Illustration: {spread.illustration_prompt}]*")

            if spread.illustration_image:
                # Reference to saved image
                lines.append("")
                lines.append(f"![Spread {spread.spread_number}](images/spread_{spread.spread_number:02d}.png)")

            lines.append("")
            lines.append("---")
            lines.append("")

        lines.append("*The End*")
        lines.append("")
        lines.append("---")
        lines.append(f"Word count: {self.word_count}")
        lines.append(f"Spreads: {self.spread_count}")
        lines.append(f"Illustrated: {'Yes' if self.is_illustrated else 'No'}")

        if self.metadata.illustration_style:
            lines.append(f"Illustration style: {self.metadata.illustration_style.name}")
            if self.metadata.style_rationale:
                lines.append(f"Style rationale: {self.metadata.style_rationale}")

        return "\n".join(lines)


# =============================================================================
# Backwards-Compatible Aliases (Deprecated)
# =============================================================================

# Alias for EntityBible (deprecated, use EntityBible instead)
CharacterBible = EntityBible

# Alias for build_entity_lookup (deprecated, use build_entity_lookup instead)
def build_character_lookup(character_bibles: list) -> dict[str, str]:
    """Deprecated: Use build_entity_lookup instead."""
    return build_entity_lookup(character_bibles)
