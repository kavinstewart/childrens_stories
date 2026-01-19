"""
DSPy Signature for extracting characters from a completed story.

Story-first workflow: after the story is written, extract what characters
appeared and how they were described, so we can generate visual bibles.
"""

import dspy


class CharacterExtractorSignature(dspy.Signature):
    """
    Extract characters from a completed children's story.

    Identify every named character that appears in the story text.
    For each character, note:
    - Their primary/shortest name (what we'll use as the canonical name)
    - All aliases (other ways they're referred to in the story: full names, titles, nicknames)
    - Everything the story tells us about them

    OUTPUT FORMAT (one character per line):
    NAME: [shortest/primary name] | ALIASES: [other names, comma-separated] | DETAILS: [everything about them]

    Examples:
    NAME: George | ALIASES: George Washington, President Washington, General Washington | DETAILS: a young boy who dreams of becoming president, wears colonial clothing, brave and curious
    NAME: Harold | ALIASES: none | DETAILS: a young boy, carries a purple crayon, goes on adventures at night, resourceful and imaginative
    NAME: Nana | ALIASES: Grandmother, CJ's grandmother | DETAILS: elderly woman, grandmother to CJ, rides the bus, deep laugh, knits, sees beauty everywhere
    NAME: Toad | ALIASES: Mr. Toad | DETAILS: a toad, best friends with Frog, shy about his bathing suit, sleeps a lot

    IMPORTANT:
    - Use the shortest, most common name as NAME (e.g., "George" not "George Washington")
    - Put all full names, titles, and variants in ALIASES
    - If a character has no aliases, write "ALIASES: none"
    - Only include characters that actually appear in the story
    """

    story_title: str = dspy.InputField(desc="The title of the story")

    story_text: str = dspy.InputField(
        desc="The complete story text (all 12 spreads)"
    )

    characters: str = dspy.OutputField(
        desc="List of characters extracted from the story. Format: 'NAME: [name] | ALIASES: [aliases] | DETAILS: [description]' - one per line."
    )
