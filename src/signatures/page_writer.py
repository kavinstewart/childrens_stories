"""
DSPy Signature for writing individual story pages.
"""

import dspy


class PageWriterSignature(dspy.Signature):
    """
    Write a single page of a children's picture book meant to be READ ALOUD by a parent.

    CRITICAL REQUIREMENTS - Your page MUST include:
    1. ONE clear action the protagonist takes
    2. ONE physical detail showing emotion (body language, not words)
    3. Dialogue that sounds like a REAL CHILD talking (if any)

    HARD BANS - NEVER do these:
    - NO rhyming dialogue or poetic speech ("A crooked brush won't fix the rush!")
    - NO cryptic riddles or philosophical questions ("What holds better—a twig or bundle?")
    - NO catchphrases repeated across pages ("Precision!")
    - NO characters who ONLY give advice - they must have their own problems
    - NO stating emotions ("He felt sad") - SHOW through body language
    - NO more than ONE sound effect word per page
    - NO tongue-twisters or alliteration pileups
    - NO sentences over 12 words

    GOOD DIALOGUE sounds like: "Wait! I can do it!" or "That's not fair." or "Oh."
    BAD DIALOGUE sounds like: "A bent plank's not broken—just listen to its song!"

    Write 30-40 words. One thing happens. A parent should enjoy reading this aloud.
    """

    story_title: str = dspy.InputField(desc="The title of the story")

    full_outline: str = dspy.InputField(
        desc="The COMPLETE story outline including protagonist goal, stakes, all characters, emotional arc, and every page's planned event"
    )

    characters: str = dspy.InputField(desc="The main characters with their behavioral quirks")

    setting: str = dspy.InputField(desc="Where the story takes place")

    page_number: int = dspy.InputField(desc="Current page number (1-indexed)")

    total_pages: int = dspy.InputField(desc="Total number of pages in the story")

    page_spec: str = dspy.InputField(
        desc="The ONE event that happens on this page, plus the emotion to show"
    )

    previous_text: str = dspy.InputField(
        desc="Text from the previous 1-2 pages for continuity (empty if first page)"
    )

    target_word_count: int = dspy.InputField(
        desc="Target number of words for this page (typically 30-40)"
    )

    page_text: str = dspy.OutputField(
        desc="30-40 words. ONE action + ONE body-language emotion detail. Dialogue must sound like real speech. No rhymes, riddles, or catchphrases. Max 12 words per sentence. Easy to read aloud."
    )

    illustration_prompt: str = dspy.OutputField(
        desc="""Visual description for the illustrator. Include:
- CHARACTERS: Who is in this scene? List by name.
- ACTION: What are they physically doing? Be specific about poses and gestures.
- EXPRESSION: What emotion shows on their face? (happy, worried, surprised, etc.)
- SETTING: Where are they? What's visible in the background?
- COMPOSITION: Where should characters be positioned? (left, center, right, foreground/background)
- FOCUS: What's the most important visual element the reader's eye should go to?
Example: "Mira (center, large) reaching up to a high shelf, face determined with tongue poking out. Kitchen background with flour-dusted counter. Papa (right, smaller) watches from doorway with gentle smile. Focus on Mira's stretching fingers."
Keep to 2-3 sentences. No dialogue or story text - just visual direction."""
    )


class PageCritiqueSignature(dspy.Signature):
    """
    Critique a children's book page against quality standards.
    Be HARSH. Real editors reject most drafts.
    """

    page_text: str = dspy.InputField(desc="The page text to critique")

    page_spec: str = dspy.InputField(desc="What was supposed to happen on this page")

    critique: str = dspy.OutputField(
        desc="List specific problems: (1) Any rhyming/poetic dialogue? (2) Any repeated catchphrases? (3) Any 'telling' instead of showing emotion? (4) Any sentences over 12 words? (5) Does it match the page spec? (6) Would a parent cringe reading this aloud? Answer YES/NO for each with brief explanation."
    )

    needs_revision: str = dspy.OutputField(
        desc="Answer YES if ANY problems exist, NO only if the page is genuinely good"
    )


class PageRevisionSignature(dspy.Signature):
    """
    Rewrite a page to fix identified problems.
    """

    original_page: str = dspy.InputField(desc="The original page text")

    critique: str = dspy.InputField(desc="The problems identified")

    page_spec: str = dspy.InputField(desc="What should happen on this page")

    characters: str = dspy.InputField(desc="Character descriptions for reference")

    revised_page: str = dspy.OutputField(
        desc="Rewritten page fixing ALL identified problems. 30-40 words. Natural dialogue. Show emotion through body language. No rhymes or riddles."
    )
