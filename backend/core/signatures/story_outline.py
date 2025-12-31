"""
DSPy Signature for generating story outlines.
"""

import dspy


class StoryOutlineSignature(dspy.Signature):
    """
    Generate an outline for a children's picture book (12 spreads, 400-600 words total).

    Write like the classics: Frog and Toad, Harold and the Purple Crayon, Sendak.
    Simple sentences. Real emotions. No lessons announced aloud.
    """

    goal: str = dspy.InputField(
        desc="The theme or concept for the story"
    )

    title: str = dspy.OutputField(desc="A fun title")

    characters: str = dspy.OutputField(
        desc="Who is in the story? Give each a name and one defining trait."
    )

    setting: str = dspy.OutputField(desc="Where and when")

    plot_summary: str = dspy.OutputField(
        desc="What happens? Keep it simple—a few sentences."
    )

    spread_breakdown: str = dspy.OutputField(
        desc="12 spreads (a spread = two facing pages). Brief notes for each: 'Spread 1: [what happens]' through 'Spread 12: [what happens]'"
    )
