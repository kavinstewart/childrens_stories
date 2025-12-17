"""
DSPy Signature for generating story outlines.
"""

import dspy


class StoryOutlineSignature(dspy.Signature):
    """
    Generate a structured outline for a children's picture book.

    STORYTELLING PRINCIPLES:
    - The protagonist needs a CLEAR, CONCRETE GOAL stated on page 1. The reader must
      be able to say "This is a story about [character] who wants [specific thing]."
    - STAKES: Why does this goal matter to the protagonist personally? What do they
      lose if they fail? Without stakes, nothing matters.
    - EMOTIONAL ARC: The protagonist must start feeling one way and end feeling
      differently. Plot serves emotion, not vice versa.
    - VULNERABILITY: Include at least one quiet moment where the protagonist feels
      doubt, sadness, or fear. Not summarized—shown. Let the reader sit with it.
    - NEVER have characters state the moral aloud. Theme emerges through consequences.
    - Characters need flaws and wants. No one exists just to teach lessons.
    - Humor should come from CHARACTER and SITUATION, not piled-up wackiness or
      random chaos. Unexpected beats random.

    AVOID: Unclear goals. Stakes that don't matter personally. Ending with a shrug
    or hedge. Characters announcing lessons. Hyperactive chaos instead of story.
    Speech-based quirks (stutters, accents) that burden read-aloud performance.
    """

    goal: str = dspy.InputField(
        desc="The learning goal or theme for the story (e.g., 'teach about sharing' or 'explain how rainbows form')"
    )

    title: str = dspy.OutputField(
        desc="An engaging, playful title that hints at fun/adventure, not the lesson"
    )

    protagonist_goal: str = dspy.OutputField(
        desc="What does the protagonist WANT? State it concretely in one sentence. This must be clear by page 1."
    )

    stakes: str = dspy.OutputField(
        desc="Why does this goal matter to the protagonist PERSONALLY? What do they lose or miss out on if they fail? Emotional stakes, not just practical ones."
    )

    characters: str = dspy.OutputField(
        desc="Main characters with: name, a VISUAL or BEHAVIORAL quirk (not speech-based), what they want, and how they act when frustrated. Supporting characters have their own imperfections and goals. Format: one character per line"
    )

    setting: str = dspy.OutputField(
        desc="Where and when the story takes place, with sensory details children can imagine"
    )

    emotional_arc: str = dspy.OutputField(
        desc="How does the protagonist FEEL at the start vs. the end? Name the emotions. Example: 'Starts: proud and dismissive. Ends: humble and grateful.' The plot exists to create this change."
    )

    plot_summary: str = dspy.OutputField(
        desc="Three-act structure: Beginning (goal established, ~25%), Middle (2-3 failures that each teach something, plus ONE quiet vulnerability moment, ~50%), End (earned success that feels different from start, ~25%). Humor comes from character, not chaos."
    )

    page_breakdown: str = dspy.OutputField(
        desc="12-16 pages. Format: 'Page N: [ONE event] + [emotion shown]'. ONE thing happens per page. Final page shows how protagonist FEELS now—no shrugs, hedges, or jokes that undercut the landing."
    )

    moral: str = dspy.OutputField(
        desc="The implicit lesson readers will FEEL through the emotional arc. For planning only—never stated aloud in the story."
    )
