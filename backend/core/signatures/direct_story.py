"""
DSPy Signature for generating a complete story directly from a goal.

This is the story-first workflow: generate the full story in one shot,
then extract characters from what was written. Replaces the outline-first
approach which invented characters before the story existed.
"""

import dspy


class DirectStorySignature(dspy.Signature):
    """
    Generate a complete children's picture book story from a goal.

    Write like the classics: Frog and Toad, Harold and the Purple Crayon,
    Last Stop on Market Street. Simple sentences. Real emotions.
    No lessons announced aloud.

    STRUCTURE:
    - 12 spreads (a spread = two facing pages when the book is open)
    - 300-400 words total (25-35 words per spread on average)
    - Target age: 4-7 years old

    PACING:
    - Spread 1: Hook. Establish character and situation.
    - Spreads 2-4: The character wants something or tries something.
    - Spreads 5-8: Complications. Things don't go as planned.
    - Spreads 9-10: Climax. The turning point.
    - Spreads 11-12: Resolution. How things have changed.

    READ-ALOUD QUALITY:
    - Short sentences (max 12 words)
    - Words that are fun to say
    - Natural rhythm when spoken

    OUTPUT FORMAT:
    TITLE: [Your title]

    Spread 1: [text]
    [Illustration: what to draw]

    Spread 2: [text]
    [Illustration: what to draw]

    ... through Spread 12
    """

    goal: str = dspy.InputField(
        desc="The theme, concept, or learning goal for the story"
    )

    reference_examples: str = dspy.InputField(
        desc="Examples of excellent children's picture book prose to learn from"
    )

    story: str = dspy.OutputField(
        desc="""Complete story with title and illustration notes.
Format:
TITLE: [title]

Spread 1: [story text]
[Illustration: scene description]

Spread 2: [story text]
[Illustration: scene description]

... through Spread 12.

Each spread: 25-35 words. Total: 300-400 words."""
    )
