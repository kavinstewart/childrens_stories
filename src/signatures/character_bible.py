"""
DSPy Signature for generating character visual bibles.
"""

import dspy


class CharacterBibleSignature(dspy.Signature):
    """
    Generate detailed visual character bibles for illustration consistency.

    For each character, define LOCKED visual attributes that must remain constant
    across all illustrations. These attributes serve as the "Visual DNA" that
    image generators will use to maintain consistency.

    OUTPUT FORMAT (one character per section, separated by blank lines):
    ```
    CHARACTER: [Name]
    SPECIES: [human/animal type - be specific]
    AGE_APPEARANCE: [specific age or age range, e.g., "7 years old" or "elderly"]
    BODY: [height relative to others, build, posture]
    FACE: [shape, skin tone, distinctive features]
    HAIR: [color, length, style, any distinctive elements]
    EYES: [color, shape, expression tendency]
    CLOTHING: [specific outfit with colors, always worn unless story requires change]
    SIGNATURE_ITEM: [one distinctive accessory or item always associated with character]
    COLOR_PALETTE: [3-4 dominant colors associated with this character]
    STYLE_TAGS: [art style descriptors, e.g., "Pixar 3D", "warm lighting", "soft edges"]
    ```

    IMPORTANT:
    - Be SPECIFIC. Not "brown hair" but "chin-length wavy auburn hair with a cowlick on the left"
    - Clothing colors must be exact: "mustard yellow raincoat" not "yellow coat"
    - Include ONE signature item that makes the character instantly recognizable
    - All characters in a story should share the same STYLE_TAGS for visual consistency
    """

    story_title: str = dspy.InputField(desc="The title of the story")
    characters_description: str = dspy.InputField(
        desc="The character descriptions from the story outline (names, quirks, roles)"
    )
    setting: str = dspy.InputField(desc="The story setting for context")

    character_bibles: str = dspy.OutputField(
        desc="Detailed visual bibles for each character following the exact format above. One character per section, blank line between characters."
    )
