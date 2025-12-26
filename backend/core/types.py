"""
Centralized domain types for the Children's Story Generator.

All dataclasses that are used across multiple modules are defined here
to make data flow explicit and avoid circular imports.
"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
import re
from io import BytesIO

# Conditional import for PIL (only needed at runtime for some methods)
if TYPE_CHECKING:
    from PIL import Image


# =============================================================================
# Style Types
# =============================================================================


@dataclass
class StyleDefinition:
    """Complete definition of an illustration style."""

    name: str
    description: str  # Human-readable description for LLM selection
    prompt_prefix: str  # Concise style direction (1-2 sentences)
    prompt_suffix: str  # Legacy field, kept for compatibility
    best_for: list[str]  # Story types this style works well for
    lighting_direction: str = ""  # Specific lighting for this style

    def apply_to_prompt(self, scene_prompt: str) -> str:
        """Wrap a scene prompt with this style's formatting."""
        return f"{self.prompt_prefix}\n\n{scene_prompt}\n\n{self.prompt_suffix}"


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


@dataclass
class CharacterReferenceSheet:
    """Generated reference image for a character."""

    character_name: str
    reference_image: bytes  # PNG/JPEG bytes of the reference portrait
    prompt_used: str = ""
    character_description: str = ""  # Age, physical features, etc. from character bible

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
        """Get reference sheet by character name (case-insensitive partial match)."""
        name_lower = character_name.lower()
        for name, sheet in self.character_sheets.items():
            if name_lower in name.lower():
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
class StoryOutline:
    """Structured representation of a story outline."""

    title: str
    characters: str
    setting: str
    plot_summary: str
    spread_breakdown: str  # 12 spreads
    goal: str  # Original goal for reference
    character_bibles: list[CharacterBible] = field(default_factory=list)
    illustration_style: Optional[StyleDefinition] = None
    style_rationale: str = ""

    def get_spreads(self) -> list[dict]:
        """Parse spread_breakdown into structured list."""
        spreads = []
        if not self.spread_breakdown:
            return spreads
        for line in self.spread_breakdown.split("\n"):
            line = line.strip()
            # Remove markdown formatting like *Spread 1* or **Spread 1**
            clean_line = re.sub(r"^\*+", "", line).strip()
            clean_line = re.sub(r"\*+$", "", clean_line.split(":")[0] if ":" in clean_line else clean_line).strip()

            if clean_line.lower().startswith("spread"):
                # Try to extract spread number and content
                parts = line.split(":", 1)
                if len(parts) == 2:
                    # Clean up the spread identifier too
                    spread_num = re.sub(r"[\*_]", "", parts[0]).strip()
                    content = parts[1].strip()
                    spreads.append({"spread": spread_num, "content": content})
        return spreads

    @property
    def spread_count(self) -> int:
        """Return the number of spreads in the outline."""
        return len(self.get_spreads())

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


@dataclass
class StorySpread:
    """Structured representation of a single story spread (two facing pages).

    A spread is a double-page unit in a picture book. Standard picture books
    have 12 spreads for story content, with 25-40 words per spread.
    """

    spread_number: int
    text: str
    word_count: int
    page_turn_note: str = ""  # What makes reader want to turn the page
    illustration_prompt: str = ""
    illustration_image: Optional[bytes] = None  # Generated illustration for this spread
    was_revised: bool = False  # Backwards compatibility

    @property
    def page_number(self) -> int:
        """Alias for spread_number (backwards compatibility)."""
        return self.spread_number

    def __str__(self) -> str:
        return f"Spread {self.spread_number}: {self.text}"


# Backwards compatibility alias
StoryPage = StorySpread


# =============================================================================
# Quality Judgment Types
# =============================================================================


@dataclass
class QualityJudgment:
    """Structured representation of a quality judgment."""

    has_critical_failures: bool
    critical_failure_reasons: str
    engagement_score: int
    read_aloud_score: int
    emotional_truth_score: int
    coherence_score: int
    chekhov_violations: str
    chekhov_score: int
    overall_score: int
    specific_problems: str
    verdict: str

    @property
    def is_excellent(self) -> bool:
        return self.verdict == "EXCELLENT" or self.overall_score >= 8

    @property
    def is_good(self) -> bool:
        return self.verdict == "GOOD" or self.overall_score >= 6

    @property
    def needs_revision(self) -> bool:
        return self.verdict in ("NEEDS_WORK", "REJECTED") or self.overall_score < 6

    @property
    def is_rejected(self) -> bool:
        return self.verdict == "REJECTED" or self.overall_score <= 3

    def get_summary(self) -> str:
        """Get a summary of the judgment."""
        summary = f"""
Quality Assessment: {self.verdict}
Overall Score: {self.overall_score}/10

Scores:
- Engagement: {self.engagement_score}/10
- Read-Aloud Quality: {self.read_aloud_score}/10
- Emotional Truth: {self.emotional_truth_score}/10
- Coherence: {self.coherence_score}/10
- Chekhov's Gun: {self.chekhov_score}/10
"""

        if self.has_critical_failures:
            summary += f"""
CRITICAL FAILURES:
{self.critical_failure_reasons}
"""

        if self.chekhov_violations and self.chekhov_violations.lower() != "none":
            summary += f"""
CHEKHOV'S GUN VIOLATIONS:
{self.chekhov_violations}
"""

        summary += f"""
Specific Problems:
{self.specific_problems}
"""
        return summary.strip()


# =============================================================================
# Complete Story Types
# =============================================================================


@dataclass
class GeneratedStory:
    """Complete generated story with all metadata."""

    title: str
    goal: str
    outline: StoryOutline
    spreads: list[StorySpread]
    judgment: Optional[QualityJudgment]
    attempts: int
    reference_sheets: Optional[StoryReferenceSheets] = None
    is_illustrated: bool = False

    @property
    def full_text(self) -> str:
        """Get the complete story text."""
        return "\n\n".join(spread.text for spread in self.spreads)

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

        lines.append(f"*The End*")
        lines.append("")
        lines.append(f"---")
        lines.append(f"Word count: {self.word_count}")
        lines.append(f"Spreads: {self.spread_count}")
        lines.append(f"Illustrated: {'Yes' if self.is_illustrated else 'No'}")

        if self.outline.illustration_style:
            lines.append(f"Illustration style: {self.outline.illustration_style.name}")
            if self.outline.style_rationale:
                lines.append(f"Style rationale: {self.outline.style_rationale}")

        if self.judgment:
            lines.append(f"Quality score: {self.judgment.overall_score}/10")
            lines.append(f"Verdict: {self.judgment.verdict}")

        return "\n".join(lines)
