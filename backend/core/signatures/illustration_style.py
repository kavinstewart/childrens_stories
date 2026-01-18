"""
DSPy Signature for selecting illustration style.
"""

import dspy


class IllustrationStyleSignature(dspy.Signature):
    """Select an illustration style for a children's book."""

    story_summary: str = dspy.InputField(desc="Title, setting, and plot")

    available_styles: str = dspy.InputField(desc="Available styles to choose from")

    selected_style: str = dspy.OutputField(
        desc="Style name (one of: watercolor_ink, digital_cartoon, pastel_soft, gouache_storybook, ghibli_inspired, claymation)"
    )

    style_rationale: str = dspy.OutputField(desc="Why this style fits (1 sentence)")
