"""
Illustration style definitions for children's book generation.

Styles are selected by the LLM based on story tone, setting, and themes.
Each style includes detailed prompt language for consistent generation.

Based on official Google documentation and proven production implementations:
- Google Cloud Imagen Prompt Guide
- Google Blog (Gemini/Imagen announcements)
- Tiny Struggles blog (production children's book app)
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


# Style definitions with detailed prompting language
ILLUSTRATION_STYLES: dict[IllustrationStyleType, StyleDefinition] = {

    IllustrationStyleType.WATERCOLOR_INK: StyleDefinition(
        name="Watercolor with Ink Linework",
        description="Soft watercolor washes combined with fine ink line work for contrast and detail. Visible brush strokes, natural texture, and gentle color gradations. Best for: nature stories, gentle emotional journeys, stories with outdoor settings.",
        prompt_prefix="Children's book illustration in watercolor style with fine ink linework.",
        prompt_suffix="""STYLE REQUIREMENTS:
- Soft watercolor washes with visible brush strokes and natural blooming texture
- Fine ink line work for contrast, detail, and character definition
- Varied ink line weights for depth; gentle cross-hatching for texture
- Limited harmonious color palette with gentle gradations
- Light, airy composition with emphasis on white space
- Hand-drawn aesthetic that embraces slight imperfections
- Warm, inviting atmosphere suitable for children""",
        best_for=["nature", "animals", "gentle emotions", "outdoor adventures", "seasons", "gardens"],
    ),

    IllustrationStyleType.DIGITAL_CARTOON: StyleDefinition(
        name="Digital Cartoon with Soft Lines",
        description="Clean digital illustration with soft, rounded lines and vibrant but not harsh colors. Clear character expressions, simple backgrounds. Best for: humorous stories, action-oriented plots, modern settings.",
        prompt_prefix="Children's book illustration in clean digital cartoon style.",
        prompt_suffix="""STYLE REQUIREMENTS:
- Clean, soft rounded lines with consistent stroke weight
- Vibrant but gentle color palette (not oversaturated)
- Simple, uncluttered backgrounds that support the characters
- Expressive character faces with clear emotions
- Slight cel-shading for depth without harsh shadows
- Modern, appealing aesthetic suitable for children
- Clear focal point with good visual hierarchy""",
        best_for=["humor", "adventure", "modern settings", "action", "friendship", "school"],
    ),

    IllustrationStyleType.PASTEL_SOFT: StyleDefinition(
        name="Pastel Illustration (Soft & Whimsical)",
        description="Gentle pastel colors with soft edges and dreamy atmosphere. Minimal harsh lines, ethereal quality. Best for: bedtime stories, dreams, magical themes, emotional comfort stories.",
        prompt_prefix="Children's book illustration in soft pastel style, gentle and dreamy.",
        prompt_suffix="""STYLE REQUIREMENTS:
- Soft pastel color palette (pale pinks, blues, lavenders, mint greens)
- Gentle, diffused edges without harsh outlines
- Dreamy, ethereal atmosphere with soft lighting
- Minimal contrast, soothing visual experience
- Whimsical, comforting mood
- Simple shapes with soft gradients
- Cozy, warm feeling suitable for young children""",
        best_for=["bedtime", "dreams", "magic", "comfort", "feelings", "lullaby", "gentle"],
    ),

    IllustrationStyleType.GOUACHE_STORYBOOK: StyleDefinition(
        name="Gouache Children's Book",
        description="Rich, opaque gouache paint style with bold colors and visible brushwork. Classic storybook aesthetic with depth and texture. Best for: traditional tales, animal stories, rich worlds.",
        prompt_prefix="Children's book illustration in traditional gouache painting style.",
        prompt_suffix="""STYLE REQUIREMENTS:
- Rich, opaque colors with visible brushwork texture
- Bold color choices with good contrast
- Classic storybook illustration aesthetic
- Layered paint effect with depth
- Warm, nostalgic feeling
- Clear character silhouettes against backgrounds
- Painterly quality with artistic brushstrokes
- Timeless children's book appearance""",
        best_for=["traditional tales", "animals", "forests", "classic stories", "rich worlds", "folklore"],
    ),

    IllustrationStyleType.GHIBLI_INSPIRED: StyleDefinition(
        name="Studio Ghibli-Inspired",
        description="Hand-drawn anime aesthetic with warm colors, painterly shading, and rich environmental detail. Emotional storytelling through visuals. Best for: adventure stories, nature themes, stories with wonder and discovery.",
        prompt_prefix="Children's book illustration in Studio Ghibli-inspired hand-drawn anime style.",
        prompt_suffix="""STYLE REQUIREMENTS:
- Soft, hand-drawn anime aesthetic with warm, vibrant colors
- Painterly shading with gentle gradients
- Rich environmental detail and atmosphere
- Expressive character designs with large, emotive eyes
- Whimsical and wondrous mood
- Nature elements rendered with care and beauty
- Soft lighting with occasional dramatic moments
- Emotional storytelling through visual composition""",
        best_for=["wonder", "discovery", "nature", "adventure", "fantasy", "journey", "growth"],
    ),

    IllustrationStyleType.CLAYMATION: StyleDefinition(
        name="Claymation / Stop-Motion Look",
        description="3D clay-like characters with textured, chunky forms and handmade aesthetic. Playful and tactile. Best for: quirky humor, inventive stories, stories about making things.",
        prompt_prefix="Children's book illustration in claymation stop-motion style.",
        prompt_suffix="""STYLE REQUIREMENTS:
- 3D clay-like characters with visible texture and fingerprint marks
- Chunky, rounded forms with a handmade aesthetic
- Warm, soft lighting as if in a miniature set
- Playful, tactile quality that children want to touch
- Simple but expressive character faces
- Miniature world feeling with attention to small details
- Cozy, crafted atmosphere
- Wallace and Gromit / Aardman-inspired warmth""",
        best_for=["humor", "quirky", "inventions", "making", "craft", "silly", "creative"],
    ),
}


def get_style(style_type: IllustrationStyleType) -> StyleDefinition:
    """Get the style definition for a given style type."""
    return ILLUSTRATION_STYLES[style_type]


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
