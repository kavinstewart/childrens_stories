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
    For each character, note their name and everything the story tells
    us about them: species (if not human), any physical descriptions,
    clothing, objects they interact with, personality shown through actions.

    OUTPUT FORMAT (one character per line):
    NAME: [name] | DETAILS: [everything the story tells us about them]

    Examples:
    NAME: Harold | DETAILS: a young boy, carries a purple crayon, goes on adventures at night, resourceful and imaginative
    NAME: Nana | DETAILS: elderly woman, grandmother to CJ, rides the bus, deep laugh, knits, sees beauty everywhere
    NAME: Toad | DETAILS: a toad, best friends with Frog, shy about his bathing suit, sleeps a lot

    Only include characters that actually appear in the story.
    Include even minor characters if they have names.
    """

    story_title: str = dspy.InputField(desc="The title of the story")

    story_text: str = dspy.InputField(
        desc="The complete story text (all 12 spreads)"
    )

    characters: str = dspy.OutputField(
        desc="List of characters extracted from the story. Format: 'NAME: [name] | DETAILS: [description]' - one per line."
    )
