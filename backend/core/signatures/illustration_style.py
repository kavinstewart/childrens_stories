"""
DSPy Signature for selecting illustration style.
"""

import dspy


class IllustrationStyleSignature(dspy.Signature):
    """
    Select the most appropriate illustration style for a children's book story.

    Consider the story's tone, setting, themes, and target emotions when choosing.
    The style should enhance the storytelling and appeal to young readers.
    """

    story_title: str = dspy.InputField(
        desc="The title of the children's story"
    )

    story_summary: str = dspy.InputField(
        desc="Brief summary of the story's plot and themes"
    )

    setting: str = dspy.InputField(
        desc="Where and when the story takes place"
    )

    emotional_arc: str = dspy.InputField(
        desc="The emotional journey of the protagonist"
    )

    available_styles: str = dspy.InputField(
        desc="List of available illustration styles with descriptions"
    )

    selected_style: str = dspy.OutputField(
        desc="The style name to use (must be one of: watercolor_ink, digital_cartoon, pastel_soft, gouache_storybook, ghibli_inspired, claymation)"
    )

    style_rationale: str = dspy.OutputField(
        desc="Brief explanation of why this style fits the story (1-2 sentences)"
    )
