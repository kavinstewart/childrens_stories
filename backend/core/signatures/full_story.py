"""
DSPy Signature for generating a complete story in one call.

This replaces the page-by-page generation approach with a single-call
approach that produces all 12 spreads at once, resulting in better
narrative coherence.
"""

import dspy


class FullStorySignature(dspy.Signature):
    """
    Generate a complete children's picture book story in one pass.

    STRUCTURE:
    - 12 spreads (a spread = two facing pages when the book is open)
    - 400-600 words total (35-50 words per spread on average)
    - Target age: 4-7 years old
    (See story_quality.py for scoring: 400-600 ideal, 300-800 acceptable)

    PAGE TURNS ARE STORY ELEMENTS:
    End each spread with something that makes readers WANT to turn the page:
    - A question ("But where could it be?")
    - Anticipation ("She took a deep breath and...")
    - A "but then" moment ("Everything was perfect. But then...")
    - Tension or surprise setup
    The next spread should deliver a satisfying payoff.

    PACING:
    - Vary the rhythm. Some spreads quieter (fewer words, reflective), others energetic.
    - Build to emotional climax around spreads 9-10, then resolve.
    - Spread 1: Hook + establish character and goal
    - Spreads 2-4: Setup and first attempts
    - Spreads 5-8: Complications, failures, vulnerability moment
    - Spreads 9-10: Climax
    - Spreads 11-12: Resolution and emotional landing

    READ-ALOUD QUALITY:
    - Short sentences (max 12 words)
    - Words that are fun to say
    - Natural rhythm when spoken
    - No rhyming dialogue or catchphrases
    - Show emotions through actions and body language, don't tell

    OUTPUT FORMAT:
    Spread 1: [text]
    Spread 2: [text]
    ... through Spread 12: [text]
    """

    outline: str = dspy.InputField(
        desc="The story outline including title, characters, setting, plot summary, and spread breakdown"
    )

    story: str = dspy.OutputField(
        desc="The complete story text. Format: 'Spread 1: [text]' through 'Spread 12: [text]'. Each spread should have 35-50 words. Total 400-600 words."
    )


class FullStoryWithPromptsSignature(dspy.Signature):
    """
    Generate a complete children's picture book story with illustration prompts.

    Same as FullStorySignature but also generates illustration prompts for each spread.
    """

    outline: str = dspy.InputField(
        desc="The story outline including title, characters, setting, plot summary, and spread breakdown"
    )

    story_with_prompts: str = dspy.OutputField(
        desc="""The complete story with illustration prompts. Format for each spread:
Spread N: [story text]
[Illustration: detailed visual description for the illustrator - characters, actions, expressions, setting details, composition]

Include all 12 spreads. Story text: 35-50 words per spread (400-600 total). Illustration prompts should describe the key visual moment."""
    )
