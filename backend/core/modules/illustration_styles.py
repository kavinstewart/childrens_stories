"""
Illustration style definitions for children's book generation.

Styles are selected by the LLM based on story tone, setting, and themes.
Optimized for Nano Banana Pro (Gemini 3 Pro Image) following Google's
recommended prompting practices:
- Concise style direction (not keyword lists)
- Specific lighting specifications
- Natural language over tag soup
"""

from enum import Enum

from ..types import StyleDefinition


class IllustrationStyleType(Enum):
    """Available illustration styles."""

    WATERCOLOR_INK = "watercolor_ink"
    DIGITAL_CARTOON = "digital_cartoon"
    PASTEL_SOFT = "pastel_soft"
    GOUACHE_STORYBOOK = "gouache_storybook"
    GHIBLI_INSPIRED = "ghibli_inspired"
    CLAYMATION = "claymation"


# Style definitions optimized for Nano Banana Pro
# Key principles: concise prefix, specific lighting, no conflicting style terms
ILLUSTRATION_STYLES: dict[IllustrationStyleType, StyleDefinition] = {

    IllustrationStyleType.WATERCOLOR_INK: StyleDefinition(
        name="Watercolor with Ink Linework",
        description="Soft watercolor washes combined with fine ink line work for contrast and detail. Visible brush strokes, natural texture, and gentle color gradations. Best for: nature stories, gentle emotional journeys, stories with outdoor settings.",
        prompt_prefix="Children's book watercolor illustration with fine ink linework, soft washes and visible brushstrokes, hand-drawn aesthetic with gentle color gradations",
        best_for=["nature", "animals", "gentle emotions", "outdoor adventures", "seasons", "gardens"],
        lighting_direction="soft diffused daylight filtering through clouds, gentle shadows with warm undertones",
    ),

    IllustrationStyleType.DIGITAL_CARTOON: StyleDefinition(
        name="Digital Cartoon with Soft Lines",
        description="Clean digital illustration with soft, rounded lines and vibrant but not harsh colors. Clear character expressions, simple backgrounds. Best for: humorous stories, action-oriented plots, modern settings.",
        prompt_prefix="Clean digital cartoon children's book illustration with soft rounded lines, vibrant gentle colors, expressive characters with clear emotions",
        best_for=["humor", "adventure", "modern settings", "action", "friendship", "school"],
        lighting_direction="bright even studio lighting with subtle cel-shading, cheerful atmosphere",
    ),

    IllustrationStyleType.PASTEL_SOFT: StyleDefinition(
        name="Pastel Illustration (Soft & Whimsical)",
        description="Gentle pastel colors with soft edges and dreamy atmosphere. Minimal harsh lines, ethereal quality. Best for: bedtime stories, dreams, magical themes, emotional comfort stories.",
        prompt_prefix="Dreamy pastel children's book illustration with soft diffused edges, ethereal pale pinks and lavenders and mint greens, whimsical and cozy",
        best_for=["bedtime", "dreams", "magic", "comfort", "feelings", "lullaby", "gentle"],
        lighting_direction="soft glowing ambient light like twilight or moonlight, minimal shadows, dreamy atmosphere",
    ),

    IllustrationStyleType.GOUACHE_STORYBOOK: StyleDefinition(
        name="Gouache Children's Book",
        description="Rich, opaque gouache paint style with bold colors and visible brushwork. Classic storybook aesthetic with depth and texture. Best for: traditional tales, animal stories, rich worlds.",
        prompt_prefix="Traditional gouache painting children's book illustration with rich opaque colors, visible painterly brushstrokes, classic timeless storybook aesthetic",
        best_for=["traditional tales", "animals", "forests", "classic stories", "rich worlds", "folklore"],
        lighting_direction="warm golden afternoon light with rich shadows, nostalgic atmosphere like classic storybooks",
    ),

    IllustrationStyleType.GHIBLI_INSPIRED: StyleDefinition(
        name="Studio Ghibli-Inspired",
        description="Hand-drawn anime aesthetic with warm colors, painterly shading, and rich environmental detail. Emotional storytelling through visuals. Best for: adventure stories, nature themes, stories with wonder and discovery.",
        prompt_prefix="Studio Ghibli-inspired hand-drawn anime children's book illustration with warm vibrant colors, painterly shading, rich environmental detail, expressive characters with large emotive eyes",
        best_for=["wonder", "discovery", "nature", "adventure", "fantasy", "journey", "growth"],
        lighting_direction="soft natural light with occasional dramatic golden rays, atmospheric depth with subtle mist or glow",
    ),

    IllustrationStyleType.CLAYMATION: StyleDefinition(
        name="Claymation / Stop-Motion Look",
        description="3D clay-like characters with textured, chunky forms and handmade aesthetic. Playful and tactile. Best for: quirky humor, inventive stories, stories about making things.",
        prompt_prefix="Claymation stop-motion style children's book illustration with 3D clay characters showing visible texture, chunky rounded handmade forms, miniature set aesthetic like Wallace and Gromit",
        best_for=["humor", "quirky", "inventions", "making", "craft", "silly", "creative"],
        lighting_direction="warm soft studio lighting as if in a miniature film set, cozy crafted atmosphere",
    ),
}


def get_style_by_name(name: str) -> StyleDefinition:
    """Get style definition by string name (case-insensitive)."""
    name_lower = name.lower().replace(" ", "_").replace("-", "_")
    for style_type in IllustrationStyleType:
        if style_type.value == name_lower:
            return ILLUSTRATION_STYLES[style_type]
    # Default to watercolor if not found
    return ILLUSTRATION_STYLES[IllustrationStyleType.WATERCOLOR_INK]


def get_all_styles_for_selection() -> str:
    """
    Format all styles for LLM selection prompt.

    Returns a formatted string describing each style option.
    """
    lines = []
    for style_type, style_def in ILLUSTRATION_STYLES.items():
        lines.append(f"- {style_type.value}: {style_def.description}")
    return "\n".join(lines)
