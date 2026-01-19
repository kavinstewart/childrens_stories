"""
DSPy Signature for generating entity visual bibles.
"""

import dspy


class EntityBibleSignature(dspy.Signature):
    """
    Generate detailed visual entity bibles for illustration consistency.

    For each entity, define LOCKED visual attributes that must remain constant
    across all illustrations. These attributes serve as the "Visual DNA" that
    image generators will use to maintain consistency.

    OUTPUT FORMAT (one entity per section, separated by blank lines):
    ```
    CHARACTER: [Name]
    SPECIES: [human/animal type - be specific]
    AGE_APPEARANCE: [specific age or age range, e.g., "7 years old" or "elderly"]
    BODY: [height relative to others, build, posture]
    FACE: [shape, skin tone, distinctive features]
    HAIR: [color, length, style, any distinctive elements]
    EYES: [color, shape, expression tendency]
    CLOTHING: [specific outfit with colors, always worn unless story requires change]
    SIGNATURE_ITEM: [one distinctive accessory or item always associated with entity]
    COLOR_PALETTE: [3-4 dominant colors associated with this entity]
    STYLE_TAGS: [art style descriptors, e.g., "Pixar 3D", "warm lighting", "soft edges"]
    ```

    IMPORTANT:
    - Be SPECIFIC. Not "brown hair" but "chin-length wavy auburn hair with a cowlick on the left"
    - Clothing colors must be exact: "mustard yellow raincoat" not "yellow coat"
    - Include ONE signature item that makes the entity instantly recognizable
    - All entities in a story should share the same STYLE_TAGS for visual consistency
    - ONLY create bibles for entities listed in extracted_entities
    """

    story_title: str = dspy.InputField(desc="The title of the story")

    story_text: str = dspy.InputField(
        desc="The complete story text - use this for context about what entities do"
    )

    extracted_entities: str = dspy.InputField(
        desc="Entities extracted from the story: 'NAME: [name] | DETAILS: [description]' format, one per line"
    )

    entity_bibles: str = dspy.OutputField(
        desc="Detailed visual bibles for each extracted entity following the exact format above. One entity per section, blank line between entities."
    )
