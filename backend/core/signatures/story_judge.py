"""
DSPy Signature for judging story quality.
"""

import dspy


class StoryJudgeSignature(dspy.Signature):
    """
    Evaluate a children's story against quality criteria.
    Be HARSH. Most children's book manuscripts get rejected.
    A 7/10 is a GOOD book. 5/10 is mediocre. 3/10 is bad.

    AUTOMATIC FAILURES (score 0-2):
    - Missing pages or "[generation failed]" text
    - Characters who only speak in rhymes or riddles
    - No clear protagonist goal
    - Moral stated explicitly by characters
    - Incoherent plot (can't follow what's happening)
    - CHEKHOV'S GUN VIOLATIONS: Objects, characters, or details introduced but never pay off

    MAJOR PROBLEMS (cap score at 4):
    - Dialogue that sounds unnatural to read aloud
    - Repeated catchphrases ("Precision!" said again and again)
    - Supporting characters who exist only to give advice
    - No humor at all
    - Telling emotion instead of showing it
    - Details that appear without setup (bandaids mentioned once, never explained)

    CHEKHOV'S GUN RULE:
    Every element introduced MUST pay off. If a character carries a flashlight, it must
    DO something important. If a character is defined, they must APPEAR. If an object
    is mentioned, it must matter to the plot. Random symbolic details that go nowhere
    are a sign of incoherent writing.

    GOOD stories (6-7) have:
    - Clear goal, real stakes, emotional arc
    - Natural dialogue a parent enjoys reading
    - At least one funny moment
    - Characters with distinct personalities
    - A satisfying ending
    - Every introduced element pays off

    EXCELLENT stories (8-10) have all of the above PLUS:
    - Memorable characters you'd want to revisit
    - Genuine emotional moments that land
    - Surprising but inevitable plot beats
    - Language that's musical without being forced
    - Tight, economical storytelling with no wasted elements
    """

    story_text: str = dspy.InputField(desc="The complete story text, page by page")

    original_goal: str = dspy.InputField(
        desc="The original learning goal or theme the story should teach"
    )

    target_age_range: str = dspy.InputField(
        desc="The target age range for readers (e.g., '3-5' or '5-8')",
        default="4-7",
    )

    has_critical_failures: bool = dspy.OutputField(
        desc="TRUE if story has: missing pages, rhyming-only dialogue, no protagonist goal, stated moral, or incoherent plot. If TRUE, overall_score MUST be 0-2."
    )

    critical_failure_reasons: str = dspy.OutputField(
        desc="If has_critical_failures is TRUE, list the specific failures. Otherwise write 'None'."
    )

    engagement_score: int = dspy.OutputField(
        desc="Score 1-10: Is it entertaining? Consider: interesting characters, fun events, humor, emotional moments. A book with NO humor caps at 5."
    )

    read_aloud_score: int = dspy.OutputField(
        desc="Score 1-10: Would a parent enjoy reading this aloud? Natural dialogue, good rhythm, no tongue-twisters, no cringe-worthy lines. Rhyming platitudes = max 3."
    )

    emotional_truth_score: int = dspy.OutputField(
        desc="Score 1-10: Do the emotions feel real and earned? Clear goal, real stakes, genuine vulnerability moment, satisfying resolution. Stated morals = max 2."
    )

    coherence_score: int = dspy.OutputField(
        desc="Score 1-10: Can you follow the story? Clear cause-and-effect, consistent characters, logical progression. If you're confused about what happened = max 4."
    )

    chekhov_violations: str = dspy.OutputField(
        desc="""List EVERY Chekhov's Gun violation:
1. Objects introduced but never used (e.g., "flashlight mentioned 3 times, never helps solve anything")
2. Characters defined but never appear (e.g., "Ms. Rosa in character list but not in story")
3. Details that appear without setup (e.g., "bandaids mentioned once on page 11, never set up")
4. Symbolic elements that don't pay off (e.g., "stars in drawing mentioned but meaning never clear")
5. Dialogue references to things not established (e.g., "'I'm scared too' but other character never said they were scared")
If none, write "None". Be thorough - this is critical."""
    )

    chekhov_score: int = dspy.OutputField(
        desc="Score 1-10: Does every introduced element pay off? 10 = tight, nothing wasted. 5 = some loose threads. 1 = multiple major elements go nowhere. If 3+ violations, cap at 4."
    )

    overall_score: int = dspy.OutputField(
        desc="Score 1-10: Overall quality. If has_critical_failures=TRUE, must be 0-2. Otherwise: average of other scores, weighted toward engagement and emotional truth."
    )

    specific_problems: str = dspy.OutputField(
        desc="List 3-5 SPECIFIC problems with exact quotes from the story showing the issue. E.g., 'Line \"A crooked brush won't fix the rush!\" is unnatural rhyming dialogue.'"
    )

    verdict: str = dspy.OutputField(
        desc="One of: 'EXCELLENT' (8+), 'GOOD' (6-7), 'NEEDS_WORK' (4-5), 'REJECTED' (0-3)"
    )
