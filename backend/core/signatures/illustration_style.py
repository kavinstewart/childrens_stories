"""
DSPy Signature for selecting illustration style.
"""

import dspy


class IllustrationStyleSignature(dspy.Signature):
    """
    Select an illustration style for a children's book.

    Match the visual style to the story's tone and content:
    - watercolor_ink: Gentle, dreamy stories. Soft emotions, nature, quiet moments.
    - digital_cartoon: Fun, energetic adventures. Humor, action, bright moods.
    - pastel_soft: Tender, reassuring stories. Bedtime, comfort, young characters.
    - gouache_storybook: Classic, timeless tales. Rich settings, traditional feel.
    - ghibli_inspired: Wonder and magic. Fantasy elements, emotional depth.
    - claymation: Quirky, tactile stories. Physical comedy, crafty themes.

    Consider the target age (4-7) and what visual style will best serve the
    emotional journey of the story.
    """

    story_summary: str = dspy.InputField(desc="Title, setting, and plot")

    available_styles: str = dspy.InputField(desc="Available styles to choose from")

    selected_style: str = dspy.OutputField(
        desc="Style name (one of: watercolor_ink, digital_cartoon, pastel_soft, gouache_storybook, ghibli_inspired, claymation)"
    )

    style_rationale: str = dspy.OutputField(desc="Why this style fits (1 sentence)")
