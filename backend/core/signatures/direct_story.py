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
    The meaning is FELT through what characters do and see, never announced.

    STRUCTURE:
    - 12 spreads (a spread = two facing pages when the book is open)
    - 400-600 words total (35-50 words per spread on average)
    - Target age: 4-7 years old
    (See story_quality.py for scoring: 400-600 ideal, 300-800 acceptable)

    PACING:
    - Spread 1: Hook. Establish character, situation, and emotional stakes.
    - Spreads 2-4: The character wants something or tries something.
    - Spreads 5-8: Complications. Things don't go as planned. Tension builds.
    - Spreads 9-10: Climax. The protagonist makes a choice or has a realization.
    - Spreads 11-12: Resolution. See below.

    THE ENDING (critical):
    Study how the reference examples END. Notice: they don't explain.
    They land on one image, one action, one moment—and stop.

    Your ending must:
    - Echo the opening. Return to the same place, image, or phrase—but shifted.
    - Show, don't tell. No narration explaining what changed or what it meant.
    - Give the protagonist agency. Their choice or realization drives the turn.
    - Leave room. The best endings open a door, not close it. Let the weight speak.
    - Linger. Ask: what single image stays with the child after the book closes?

    For weighty stories (loss, courage, sacrifice): let silence carry the meaning.
    The feeling should echo after the last word. Don't rush. Don't explain.

    READ-ALOUD QUALITY:
    - Short sentences (max 12 words)
    - Words that are fun to say
    - Natural rhythm when spoken

    OUTPUT FORMAT:
    TITLE: [Your title]

    Spread 1: [text]
    [Illustration: what to draw]
    [Characters: comma-separated names of characters VISIBLE in the illustration]

    Spread 2: [text]
    [Illustration: what to draw]
    [Characters: comma-separated names of characters VISIBLE in the illustration]

    ... through Spread 12

    CRITICAL - [Characters:] field is REQUIRED for EVERY spread:
    - You MUST include a [Characters: ...] line for every single spread
    - List ONLY characters who should be VISIBLE in the illustration
    - If a character hasn't appeared yet in the story, do NOT include them
    - If NO characters are visible (e.g., empty room, landscape), write: [Characters: none]
    - Be precise: if the text says "soldiers grumbled" but the General hasn't arrived yet, don't list the General
    - Missing [Characters:] fields will cause illustration errors - do NOT skip this field
    """

    goal: str = dspy.InputField(
        desc="The theme, concept, or learning goal for the story"
    )

    reference_examples: str = dspy.InputField(
        desc="Examples of excellent children's picture book prose to learn from"
    )

    story: str = dspy.OutputField(
        desc="""Complete story with title, illustration notes, and character presence.
Format:
TITLE: [title]

Spread 1: [story text]
[Illustration: scene description]
[Characters: names of characters visible in this illustration, or "none"]

Spread 2: [story text]
[Illustration: scene description]
[Characters: names visible in illustration]

... through Spread 12.

Each spread: 35-50 words. Total: 400-600 words.
CRITICAL: [Characters: ...] is REQUIRED for EVERY spread - never omit it.
Characters field must list ONLY characters who appear in THAT spread's illustration, or "none" if empty."""
    )
