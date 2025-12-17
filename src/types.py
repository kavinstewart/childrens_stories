"""
Centralized domain types for the Children's Story Generator.

All dataclasses that are used across multiple modules are defined here
to make data flow explicit and avoid circular imports.
"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
import os
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
    prompt_prefix: str  # Added to start of illustration prompts
    prompt_suffix: str  # Added to end of illustration prompts
    best_for: list[str]  # Story types this style works well for

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

    def save(self, output_dir: str) -> str:
        """Save the reference image to a file."""
        os.makedirs(output_dir, exist_ok=True)
        safe_name = "".join(c if c.isalnum() else "_" for c in self.character_name)
        path = os.path.join(output_dir, f"{safe_name}_reference.png")
        with open(path, "wb") as f:
            f.write(self.reference_image)
        return path

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

    def save_all(self, output_dir: str) -> list[str]:
        """Save all reference sheets to directory."""
        paths = []
        for sheet in self.character_sheets.values():
            path = sheet.save(output_dir)
            paths.append(path)
        return paths


# =============================================================================
# Story Structure Types
# =============================================================================


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


@dataclass
class StoryPage:
    """Structured representation of a single story page."""

    page_number: int
    text: str
    word_count: int
    was_revised: bool = False
    illustration_prompt: str = ""
    illustration_image: Optional[bytes] = None  # Generated illustration

    def __str__(self) -> str:
        return f"Page {self.page_number}: {self.text}"


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
    pages: list[StoryPage]
    judgment: Optional[QualityJudgment]
    attempts: int
    reference_sheets: Optional[StoryReferenceSheets] = None
    is_illustrated: bool = False

    @property
    def full_text(self) -> str:
        """Get the complete story text."""
        return "\n\n".join(page.text for page in self.pages)

    @property
    def word_count(self) -> int:
        """Total word count of the story."""
        return sum(page.word_count for page in self.pages)

    @property
    def page_count(self) -> int:
        """Number of pages in the story."""
        return len(self.pages)

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

        for page in self.pages:
            lines.append(f"**Page {page.page_number}**")
            lines.append("")
            lines.append(page.text)

            if include_illustration_prompts and page.illustration_prompt:
                lines.append("")
                lines.append(f"*[Illustration: {page.illustration_prompt}]*")

            if page.illustration_image:
                # Reference to saved image
                lines.append("")
                lines.append(f"![Page {page.page_number}](images/page_{page.page_number:02d}.png)")

            lines.append("")
            lines.append("---")
            lines.append("")

        lines.append(f"*The End*")
        lines.append("")
        lines.append(f"---")
        lines.append(f"Word count: {self.word_count}")
        lines.append(f"Pages: {self.page_count}")
        lines.append(f"Illustrated: {'Yes' if self.is_illustrated else 'No'}")

        if self.outline.illustration_style:
            lines.append(f"Illustration style: {self.outline.illustration_style.name}")
            if self.outline.style_rationale:
                lines.append(f"Style rationale: {self.outline.style_rationale}")

        if self.judgment:
            lines.append(f"Quality score: {self.judgment.overall_score}/10")
            lines.append(f"Verdict: {self.judgment.verdict}")

        return "\n".join(lines)

    def save_illustrated(self, output_dir: str) -> dict[str, str]:
        """
        Save the illustrated story to a directory.

        Creates:
        - story.md: The formatted story text
        - images/: Directory with page illustrations
        - character_refs/: Directory with character reference sheets

        Returns:
            Dict with paths to saved files
        """
        os.makedirs(output_dir, exist_ok=True)
        paths = {"output_dir": output_dir}

        # Save story markdown
        story_path = os.path.join(output_dir, "story.md")
        with open(story_path, "w") as f:
            f.write(self.to_formatted_string(include_illustration_prompts=True))
        paths["story_md"] = story_path

        # Save page illustrations
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        paths["images"] = []
        for page in self.pages:
            if page.illustration_image:
                img_path = os.path.join(images_dir, f"page_{page.page_number:02d}.png")
                with open(img_path, "wb") as f:
                    f.write(page.illustration_image)
                paths["images"].append(img_path)

        # Save character reference sheets
        if self.reference_sheets:
            refs_dir = os.path.join(output_dir, "character_refs")
            ref_paths = self.reference_sheets.save_all(refs_dir)
            paths["character_refs"] = ref_paths

        return paths
