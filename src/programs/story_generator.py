"""
Main DSPy Program for generating children's stories.

Composes OutlineGenerator, PageGenerator, QualityJudge,
CharacterSheetGenerator, and PageIllustrator into a complete
pipeline with quality iteration loop and illustration generation.
"""

import dspy

from ..types import GeneratedStory
from ..modules.outline_generator import OutlineGenerator
from ..modules.page_generator import PageGenerator
from ..modules.quality_judge import QualityJudge
from ..modules.character_sheet_generator import CharacterSheetGenerator
from ..modules.page_illustrator import PageIllustrator
from ..config import STORY_CONSTANTS, get_default_lm


class StoryGenerator(dspy.Module):
    """
    Complete story generation pipeline.

    Pipeline:
    1. Generate outline from goal
    2. Generate pages from outline
    3. Judge quality
    4. If quality < threshold, retry with feedback (up to max_attempts)

    Args:
        quality_threshold: Minimum score (0-10) to accept a story
        max_attempts: Maximum generation attempts
        words_per_page: Target words per page
        lm: Optional explicit LM to use. If provided, bypasses global
            dspy.configure() state. Useful for testing and explicit control.
    """

    def __init__(
        self,
        quality_threshold: int = 7,
        max_attempts: int = 3,
        words_per_page: int = 35,
        lm: dspy.LM = None,
    ):
        super().__init__()
        self.outline_generator = OutlineGenerator()
        self.page_generator = PageGenerator()
        self.quality_judge = QualityJudge()

        self.quality_threshold = quality_threshold
        self.max_attempts = max_attempts
        self.words_per_page = words_per_page
        self._lm = lm  # Store explicit LM if provided

    def forward(
        self,
        goal: str,
        target_age_range: str = "4-7",
        skip_quality_loop: bool = False,
    ) -> GeneratedStory:
        """
        Generate a complete children's story.

        Args:
            goal: The learning goal or theme for the story
            target_age_range: Target reader age range
            skip_quality_loop: If True, generate once without quality iteration

        Returns:
            GeneratedStory with all components
        """
        # Use explicit LM if provided, otherwise use global config
        if self._lm is not None:
            with dspy.context(lm=self._lm):
                return self._generate_story(goal, target_age_range, skip_quality_loop)
        else:
            return self._generate_story(goal, target_age_range, skip_quality_loop)

    def _generate_story(
        self,
        goal: str,
        target_age_range: str,
        skip_quality_loop: bool,
    ) -> GeneratedStory:
        """Internal method that does the actual generation."""
        best_story = None
        best_score = 0

        for attempt in range(1, self.max_attempts + 1):
            # Enhance goal with feedback from previous attempt
            current_goal = goal
            if best_story and best_story.judgment:
                current_goal = (
                    f"{goal}\n\n"
                    f"AVOID THESE PROBLEMS from previous attempt:\n{best_story.judgment.specific_problems}"
                )

            # Step 1: Generate outline
            outline = self.outline_generator(goal=current_goal, debug=True)

            # Step 2: Generate all pages
            pages = self.page_generator.generate_all_pages(
                outline=outline,
                words_per_page=self.words_per_page,
            )

            # Compile story text for judging
            story_text = "\n\n".join(
                f"Page {p.page_number}: {p.text}" for p in pages
            )

            # Step 3: Judge quality (unless skipped)
            judgment = None
            if not skip_quality_loop:
                judgment = self.quality_judge(
                    story_text=story_text,
                    original_goal=goal,
                    target_age_range=target_age_range,
                )

            story = GeneratedStory(
                title=outline.title,
                goal=goal,
                outline=outline,
                pages=pages,
                judgment=judgment,
                attempts=attempt,
            )

            # Track best story
            current_score = judgment.overall_score if judgment else 10
            if current_score > best_score:
                best_score = current_score
                best_story = story

            # Check if quality is good enough
            if skip_quality_loop or (judgment and judgment.overall_score >= self.quality_threshold):
                return story

        # Return best attempt if we exhausted retries
        return best_story

    def generate_simple(self, goal: str) -> GeneratedStory:
        """
        Generate a story without quality iteration (faster, cheaper).

        Args:
            goal: The learning goal or theme

        Returns:
            GeneratedStory (single attempt, no quality judgment)
        """
        return self.forward(goal=goal, skip_quality_loop=True)

    def generate_illustrated(
        self,
        goal: str,
        target_age_range: str = "4-7",
        skip_quality_loop: bool = False,
        use_image_qa: bool = True,
        max_image_attempts: int = 3,
        debug: bool = False,
    ) -> GeneratedStory:
        """
        Generate a complete illustrated children's story using Nano Banana Pro.

        Full pipeline:
        1. Generate story outline (with character bibles)
        2. Generate story pages (with illustration prompts)
        3. Judge quality and iterate
        4. Generate character reference portraits
        5. Generate page illustrations using reference images (with QA)

        Args:
            goal: The learning goal or theme for the story
            target_age_range: Target reader age range
            skip_quality_loop: If True, skip quality iteration
            use_image_qa: If True, run QA on images and regenerate failures
            max_image_attempts: Max regeneration attempts per image
            debug: Print progress info

        Returns:
            GeneratedStory with illustrations
        """
        import sys

        # Step 1-3: Generate the story text
        if debug:
            print("Step 1: Generating story text...", file=sys.stderr)
        story = self.forward(
            goal=goal,
            target_age_range=target_age_range,
            skip_quality_loop=skip_quality_loop,
        )

        if debug and story.outline.illustration_style:
            print(f"Selected illustration style: {story.outline.illustration_style.name}", file=sys.stderr)
            print(f"  Rationale: {story.outline.style_rationale}", file=sys.stderr)

        # Step 4: Generate character reference images
        if debug:
            print(f"Step 2: Generating reference images for {len(story.outline.character_bibles)} characters...", file=sys.stderr)

        sheet_generator = CharacterSheetGenerator()
        reference_sheets = sheet_generator.generate_for_story(
            outline=story.outline,
            debug=debug,
        )
        story.reference_sheets = reference_sheets

        # Step 5: Generate page illustrations (with QA if enabled)
        if debug:
            print(f"Step 3: Generating {len(story.pages)} page illustrations...", file=sys.stderr)
            if use_image_qa:
                print(f"  QA enabled: max {max_image_attempts} attempts per image", file=sys.stderr)

        illustrator = PageIllustrator()

        if use_image_qa:
            story.pages, qa_summary = illustrator.illustrate_story_with_qa(
                pages=story.pages,
                outline=story.outline,
                reference_sheets=reference_sheets,
                max_attempts_per_page=max_image_attempts,
                debug=debug,
            )
            if debug:
                print(f"\nQA Results: {qa_summary['passed']}/{qa_summary['total_pages']} passed", file=sys.stderr)
                print(f"  Total regenerations: {qa_summary['regenerations']}", file=sys.stderr)
                if qa_summary['issues_by_type']:
                    print(f"  Issues: {qa_summary['issues_by_type']}", file=sys.stderr)
        else:
            story.pages = illustrator.illustrate_story(
                pages=story.pages,
                outline=story.outline,
                reference_sheets=reference_sheets,
                debug=debug,
            )

        story.is_illustrated = True

        if debug:
            illustrated_count = sum(1 for p in story.pages if p.illustration_image)
            print(f"Done! {illustrated_count}/{len(story.pages)} pages illustrated.", file=sys.stderr)

        return story
