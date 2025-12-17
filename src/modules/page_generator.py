"""
DSPy Module for generating individual story pages with self-critique.
"""

import dspy
from pathlib import Path

from ..types import StoryOutline, StoryPage
from ..signatures.page_writer import (
    PageWriterSignature,
    PageCritiqueSignature,
    PageRevisionSignature,
)


class PageGenerator(dspy.Module):
    """
    Generate individual pages of a children's story with self-critique loop.

    Key improvements based on research:
    1. Full outline context for every page (GOAT-Storytelling approach)
    2. Self-critique and revision loop (AIMuse finding)
    3. Explicit bans and requirements (Mazur benchmark approach)
    """

    def __init__(self, use_optimized: bool = False, max_revisions: int = 2):
        super().__init__()

        self.max_revisions = max_revisions

        optimized_path = (
            Path(__file__).parent.parent.parent / "optimized" / "page_writer_optimized.json"
        )

        # Page writer - generates initial draft
        if use_optimized and optimized_path.exists():
            self.write_page = dspy.ChainOfThought(PageWriterSignature)
            self.write_page.load(str(optimized_path))
        else:
            self.write_page = dspy.ChainOfThought(PageWriterSignature)

        # Critique and revision modules for self-editing chain
        self.critique_page = dspy.ChainOfThought(PageCritiqueSignature)
        self.revise_page = dspy.ChainOfThought(PageRevisionSignature)

    def _format_full_outline(self, outline: StoryOutline) -> str:
        """Format the complete outline for context injection."""
        return f"""STORY: {outline.title}

PROTAGONIST GOAL: {outline.protagonist_goal}

STAKES: {outline.stakes}

CHARACTERS:
{outline.characters}

SETTING: {outline.setting}

EMOTIONAL ARC: {outline.emotional_arc}

PLOT SUMMARY:
{outline.plot_summary}

PAGE-BY-PAGE PLAN:
{outline.page_breakdown}

IMPLICIT MORAL (never state aloud): {outline.moral}"""

    def forward(
        self,
        outline: StoryOutline,
        page_number: int,
        page_spec: str,
        previous_text: str = "",
        target_word_count: int = 35,
    ) -> StoryPage:
        """
        Generate a single page with self-critique loop.

        Args:
            outline: The story outline for FULL context
            page_number: Current page number (1-indexed)
            page_spec: What should happen on this page
            previous_text: Text from previous pages for continuity
            target_word_count: Target words for this page

        Returns:
            StoryPage with revised text
        """
        pages = outline.get_pages()
        total_pages = len(pages) if pages else 16

        # Format full outline for context (GOAT approach)
        full_outline = self._format_full_outline(outline)

        # Generate initial draft
        page_text = None
        illustration_prompt = ""
        last_error = None
        for attempt in range(3):
            spec_with_attempt = (
                page_spec if attempt == 0 else f"{page_spec} (attempt {attempt + 1})"
            )

            try:
                result = self.write_page(
                    story_title=outline.title or "Untitled",
                    full_outline=full_outline,
                    characters=outline.characters or "",
                    setting=outline.setting or "",
                    page_number=page_number,
                    total_pages=total_pages,
                    page_spec=spec_with_attempt,
                    previous_text=previous_text,
                    target_word_count=target_word_count,
                )

                if result.page_text:
                    page_text = result.page_text
                    illustration_prompt = getattr(result, 'illustration_prompt', '') or ""
                    break
                else:
                    last_error = f"page_text was None/empty. Result attrs: {[a for a in dir(result) if not a.startswith('_')]}"
                    import sys
                    print(f"DEBUG Page {page_number} attempt {attempt+1}: {last_error}", file=sys.stderr)
            except Exception as e:
                last_error = str(e)
                import sys
                print(f"DEBUG Page {page_number} attempt {attempt+1} EXCEPTION: {last_error}", file=sys.stderr)

        if not page_text:
            import sys
            print(f"ERROR Page {page_number} FAILED. Last error: {last_error}", file=sys.stderr)
            return StoryPage(
                page_number=page_number,
                text=f"[Page {page_number} - generation failed after 3 attempts]",
                word_count=0,
                was_revised=False,
                illustration_prompt="",
            )

        # Self-critique loop (AIMuse approach)
        was_revised = False
        for revision_round in range(self.max_revisions):
            # Critique the current draft
            critique_result = self.critique_page(
                page_text=page_text,
                page_spec=page_spec,
            )

            # Check if revision needed
            needs_revision = critique_result.needs_revision
            if isinstance(needs_revision, str):
                needs_revision = needs_revision.lower().strip() in ("true", "yes", "1", "y")
            elif isinstance(needs_revision, bool):
                pass  # already a bool
            else:
                needs_revision = False

            if not needs_revision:
                break

            # Revise based on critique
            revision_result = self.revise_page(
                original_page=page_text,
                critique=critique_result.critique or "",
                page_spec=page_spec,
                characters=outline.characters or "",
            )

            if revision_result.revised_page:
                page_text = revision_result.revised_page
                was_revised = True

        return StoryPage(
            page_number=page_number,
            text=page_text,
            word_count=len(page_text.split()),
            was_revised=was_revised,
            illustration_prompt=illustration_prompt,
        )

    def generate_all_pages(
        self, outline: StoryOutline, words_per_page: int = 35
    ) -> list[StoryPage]:
        """
        Generate all pages for a story from the outline.

        Args:
            outline: The complete story outline
            words_per_page: Target words per page

        Returns:
            List of StoryPage objects
        """
        pages_spec = outline.get_pages()
        if not pages_spec:
            # Fallback if page parsing fails
            pages_spec = [
                {"page": f"Page {i+1}", "content": f"Story content for page {i+1}"}
                for i in range(16)
            ]

        generated_pages = []
        previous_text = ""

        for i, page_info in enumerate(pages_spec):
            page_num = i + 1
            page_spec = page_info.get("content", f"Continue the story on page {page_num}")

            page = self.forward(
                outline=outline,
                page_number=page_num,
                page_spec=page_spec,
                previous_text=previous_text,
                target_word_count=words_per_page,
            )

            generated_pages.append(page)

            # Update previous text for continuity (keep last 2 pages)
            if len(generated_pages) >= 2:
                previous_text = f"{generated_pages[-2].text}\n\n{generated_pages[-1].text}"
            else:
                previous_text = page.text

        return generated_pages
