"""
Centralized domain types for the Children's Story Generator.

All dataclasses that are used across multiple modules are defined here
to make data flow explicit and avoid circular imports.
"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
import re
from io import BytesIO


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


def _names_match(query: str, canonical: str) -> bool:
    """
    Check if query matches canonical name using normalization and article-stripping.

    Supports exact match and article-stripped match (e.g., "Blue Bird" matches "The Blue Bird").
    Does NOT use substring matching to avoid false positives.
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

    return False


def build_character_lookup(character_bibles: list) -> dict[str, str]:
    """
    Build a lookup dict mapping normalized names (and variants) to canonical names.

    Args:
        character_bibles: List of CharacterBible objects

    Returns:
        Dict mapping normalized name variants -> canonical character name
    """
    lookup = {}
    for bible in character_bibles:
        canonical = bible.name
        # Add normalized canonical name
        normalized = _normalize_name(canonical)
        lookup[normalized] = canonical
        # Add article-stripped variant
        stripped = _strip_leading_article(canonical)
        if stripped != normalized:
            lookup[stripped] = canonical
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

Wide shot framing with space at bottom for text overlay. Maintain exact character identity from reference images above."""


# =============================================================================
# Character Types
# =============================================================================


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
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterBible":
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
        )


@dataclass
class CharacterReferenceSheet:
    """Generated reference image for a character."""

    character_name: str
    reference_image: bytes  # PNG/JPEG bytes of the reference portrait
    prompt_used: str = ""
    character_description: str = ""  # Age, physical features, etc. from character bible
    bible: Optional["CharacterBible"] = None  # Full character bible for editing

    def to_pil_image(self) -> "Image.Image":
        """Convert to PIL Image for passing to Nano Banana Pro."""
        from PIL import Image
        return Image.open(BytesIO(self.reference_image))


@dataclass
class StoryReferenceSheets:
    """All reference sheets for a story."""

    story_title: str
    character_sheets: dict[str, CharacterReferenceSheet] = field(default_factory=dict)

    def get_sheet(self, character_name: str) -> Optional[CharacterReferenceSheet]:
        """Get reference sheet by character name.

        Uses exact matching with normalization and article-stripping.
        Does NOT use substring matching to avoid false positives.

        Args:
            character_name: Name to search for (e.g., "Blue Bird" matches "The Blue Bird")

        Returns:
            CharacterReferenceSheet if found, None otherwise
        """
        for name, sheet in self.character_sheets.items():
            if _names_match(character_name, name):
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
    """Metadata for story illustration: style and characters.

    This is NOT an outline - the story-first workflow generates the complete
    story directly. This container holds metadata needed for illustration:
    - Character visual descriptions (bibles) for consistent illustration
    - Selected illustration style
    - Title for reference
    """

    title: str
    character_bibles: list[CharacterBible] = field(default_factory=list)
    illustration_style: Optional[StyleDefinition] = None
    style_rationale: str = ""

    def get_character_bible(self, name: str) -> Optional[CharacterBible]:
        """Find a character bible by name.

        Uses exact matching with normalization and article-stripping.
        Does NOT use substring matching to avoid false positives.

        Args:
            name: Name to search for (e.g., "Blue Bird" matches "The Blue Bird")

        Returns:
            CharacterBible if found, None otherwise
        """
        for bible in self.character_bibles:
            if _names_match(name, bible.name):
                return bible
        return None


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
    # Required for illustration - DirectStoryGenerator must populate this field
    present_characters: Optional[list[str]] = None

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

        if self.judgment:
            lines.append(f"Quality score: {self.judgment.overall_score}/10")
            lines.append(f"Verdict: {self.judgment.verdict}")

        return "\n".join(lines)
