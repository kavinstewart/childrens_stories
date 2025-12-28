"""
Main DSPy Program for generating children's stories.

Story-first workflow:
1. Generate the complete story directly from the goal (one LLM call)
2. Extract characters from what was written
3. Generate character bibles for illustration consistency
4. Select illustration style
5. (Optional) Judge quality and iterate

A spread = two facing pages when the book is open. A 32-page picture book
has 12 spreads of story content.

Includes retry with exponential backoff for transient network errors.
"""

import dspy

from backend.config import llm_retry
from ..types import GeneratedStory, StoryOutline
from ..modules.direct_story_generator import DirectStoryGenerator
from ..modules.character_extractor import CharacterExtractor
from ..modules.bible_generator import BibleGenerator
from ..modules.quality_judge import QualityJudge
from ..modules.character_sheet_generator import CharacterSheetGenerator
from ..modules.spread_illustrator import SpreadIllustrator
from ..modules.illustration_styles import get_style_by_name, get_all_styles_for_selection
from ..signatures.illustration_style import IllustrationStyleSignature


class StoryGenerator(dspy.Module):
    """
    Complete story generation pipeline using story-first workflow.

    Pipeline:
    1. Generate complete story from goal (title + 12 spreads in one call)
    2. Extract characters from the written story
    3. Generate character bibles for illustration consistency
    4. Select illustration style based on story content
    5. (Optional) Judge quality and retry if needed

    Args:
        quality_threshold: Minimum score (0-10) to accept a story
        max_attempts: Maximum generation attempts
        lm: Optional explicit LM to use. If provided, bypasses global
            dspy.configure() state. Useful for testing and explicit control.
        include_examples: Whether to include reference story examples in prompt
        example_count: Number of reference examples to include (1-2 recommended)
    """

    def __init__(
        self,
        quality_threshold: int = 7,
        max_attempts: int = 3,
        lm: dspy.LM = None,
        include_examples: bool = True,
        example_count: int = 1,
    ):
        super().__init__()
        self.story_generator = DirectStoryGenerator(
            include_examples=include_examples,
            example_count=example_count,
        )
        self.character_extractor = CharacterExtractor()
        self.bible_generator = BibleGenerator()
        self.style_selector = dspy.ChainOfThought(IllustrationStyleSignature)
        self.quality_judge = QualityJudge()

        self.quality_threshold = quality_threshold
        self.max_attempts = max_attempts
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
        import sys

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

            # Step 1: Generate complete story (with retry for network errors)
            title, spreads = llm_retry(self.story_generator)(
                goal=current_goal,
                debug=True,
            )

            # Compile story text for downstream processing
            story_text = "\n\n".join(
                f"Spread {s.spread_number}: {s.text}" for s in spreads
            )

            # Step 2: Extract characters from the story
            extracted_characters = llm_retry(self.character_extractor)(
                title=title,
                story_text=story_text,
                debug=True,
            )

            # Step 3: Generate character bibles
            character_bibles = llm_retry(self.bible_generator)(
                title=title,
                story_text=story_text,
                extracted_characters=extracted_characters,
                debug=True,
            )

            # Steps 4 & 5: Select illustration style AND judge quality (in parallel)
            import concurrent.futures

            story_summary = f"{title}. {story_text[:500]}..."

            def select_style():
                result = llm_retry(self.style_selector)(
                    story_summary=story_summary,
                    available_styles=get_all_styles_for_selection(),
                )
                return result

            def judge_quality():
                if skip_quality_loop:
                    return None
                return llm_retry(self.quality_judge)(
                    story_text=story_text,
                    original_goal=goal,
                    target_age_range=target_age_range,
                )

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                style_future = executor.submit(select_style)
                judge_future = executor.submit(judge_quality)

                style_result = style_future.result()
                judgment = judge_future.result()

            selected_style_name = style_result.selected_style.strip().lower()
            illustration_style = get_style_by_name(selected_style_name)

            print(f"DEBUG Selected style: {selected_style_name}", file=sys.stderr)

            # Build outline object for downstream compatibility
            outline = StoryOutline(
                title=title,
                characters="",  # Not used in story-first workflow
                setting="",  # Extracted from story context in illustrations
                plot_summary="",  # Not used in story-first workflow
                spread_breakdown="",  # Not used in story-first workflow
                goal=goal,
                character_bibles=character_bibles,
                illustration_style=illustration_style,
                style_rationale=style_result.style_rationale,
            )

            story = GeneratedStory(
                title=title,
                goal=goal,
                outline=outline,
                spreads=spreads,
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
        on_progress: callable = None,
    ) -> GeneratedStory:
        """
        Generate a complete illustrated children's story using Nano Banana Pro.

        Full pipeline:
        1. Generate story outline (with character bibles and spread breakdown)
        2. Generate all 12 spreads in a single LLM call (with illustration prompts)
        3. Judge quality and iterate
        4. Generate character reference portraits
        5. Generate 12 spread illustrations using reference images (with QA)

        Args:
            goal: The learning goal or theme for the story
            target_age_range: Target reader age range
            skip_quality_loop: If True, skip quality iteration
            use_image_qa: If True, run QA on images and regenerate failures
            max_image_attempts: Max regeneration attempts per image
            debug: Print progress info
            on_progress: Optional callback(stage, detail, completed, total) for progress updates

        Returns:
            GeneratedStory with illustrations
        """
        import sys

        # Step 1-3: Generate the story text (outline + 12 spreads)
        if debug:
            print("Step 1: Generating story text (12 spreads)...", file=sys.stderr)
        if on_progress:
            on_progress("outline", "Crafting your story...", None, None)

        story = self.forward(
            goal=goal,
            target_age_range=target_age_range,
            skip_quality_loop=skip_quality_loop,
        )

        if on_progress:
            on_progress("spreads", "Story text complete", 1, 1)

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
            on_progress=on_progress,
        )
        story.reference_sheets = reference_sheets

        # Step 5: Generate spread illustrations (12 images, with QA if enabled)
        if debug:
            print(f"Step 3: Generating {len(story.spreads)} spread illustrations...", file=sys.stderr)
            if use_image_qa:
                print(f"  QA enabled: max {max_image_attempts} attempts per image", file=sys.stderr)

        illustrator = SpreadIllustrator()

        if use_image_qa:
            story.spreads, qa_summary = illustrator.illustrate_story_with_qa(
                spreads=story.spreads,
                outline=story.outline,
                reference_sheets=reference_sheets,
                max_attempts_per_spread=max_image_attempts,
                debug=debug,
                on_progress=on_progress,
            )
            if debug:
                print(f"\nQA Results: {qa_summary['passed']}/{qa_summary['total_spreads']} passed", file=sys.stderr)
                print(f"  Total regenerations: {qa_summary['regenerations']}", file=sys.stderr)
                if qa_summary['issues_by_type']:
                    print(f"  Issues: {qa_summary['issues_by_type']}", file=sys.stderr)
        else:
            story.spreads = illustrator.illustrate_story(
                spreads=story.spreads,
                outline=story.outline,
                reference_sheets=reference_sheets,
                debug=debug,
                on_progress=on_progress,
            )

        story.is_illustrated = True

        if debug:
            illustrated_count = sum(1 for s in story.spreads if s.illustration_image)
            print(f"Done! {illustrated_count}/{len(story.spreads)} spreads illustrated.", file=sys.stderr)

        return story
