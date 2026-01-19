"""
Main DSPy Program for generating children's stories.

Inline Entity Tagging workflow:
1. Generate the complete story with entity definitions (one LLM call)
2. Generate character bibles from entity definitions
3. Select illustration style

A spread = two facing pages when the book is open. A 32-page picture book
has 12 spreads of story content.

Includes retry with exponential backoff for transient network errors.
"""

import dspy

from backend.config import llm_retry
from ..types import GeneratedStory, StoryMetadata, StorySpread
from ..modules.direct_story_generator import DirectStoryGenerator
from ..modules.bible_generator import BibleGenerator
from ..modules.character_sheet_generator import CharacterSheetGenerator
from ..modules.spread_illustrator import SpreadIllustrator
from ..modules.illustration_styles import get_style_by_name, get_all_styles_for_selection
from ..signatures.illustration_style import IllustrationStyleSignature


def _format_spreads_for_llm(spreads: list[StorySpread]) -> str:
    """Format spreads with numbered prefixes for LLM context."""
    return "\n\n".join(f"Spread {s.spread_number}: {s.text}" for s in spreads)


class StoryGenerator(dspy.Module):
    """
    Complete story generation pipeline using inline entity tagging.

    Pipeline:
    1. Generate complete story from goal (title + 12 spreads + entity definitions)
    2. Generate character bibles from entity definitions
    3. Select illustration style based on story content

    Inline entity tagging: DirectStoryGenerator now outputs entity definitions
    (@e1, @e2, etc.) directly, eliminating the need for character extraction.

    Args:
        lm: Optional explicit LM to use. If provided, bypasses global
            dspy.configure() state. Useful for testing and explicit control.
        include_examples: Whether to include reference story examples in prompt
        example_count: Number of reference examples to include (1-2 recommended)
    """

    def __init__(
        self,
        lm: dspy.LM = None,
        include_examples: bool = True,
        example_count: int = 1,
        # Deprecated params - kept for backwards compatibility, ignored
        quality_threshold: int = None,
        max_attempts: int = None,
    ):
        super().__init__()
        self.story_generator = DirectStoryGenerator(
            include_examples=include_examples,
            example_count=example_count,
        )
        self.bible_generator = BibleGenerator()
        self.style_selector = dspy.ChainOfThought(IllustrationStyleSignature)
        self._lm = lm  # Store explicit LM if provided

    def forward(
        self,
        goal: str,
        target_age_range: str = "4-7",
    ) -> GeneratedStory:
        """
        Generate a complete children's story.

        Args:
            goal: The learning goal or theme for the story
            target_age_range: Target reader age range (for future use)

        Returns:
            GeneratedStory with all components
        """
        # Use explicit LM if provided, otherwise use global config
        if self._lm is not None:
            with dspy.context(lm=self._lm):
                return self._generate_story(goal)
        else:
            return self._generate_story(goal)

    def _generate_story(self, goal: str) -> GeneratedStory:
        """Internal method that does the actual generation."""
        import sys

        # Step 1: Generate complete story with entity definitions (with retry)
        title, spreads, entity_definitions = llm_retry(self.story_generator)(
            goal=goal,
            debug=True,
        )

        if entity_definitions:
            print(f"DEBUG Extracted {len(entity_definitions)} entities: {list(entity_definitions.keys())}", file=sys.stderr)
        else:
            print("WARNING: No entity definitions returned - story may use legacy format", file=sys.stderr)

        # Compile story text for downstream processing
        story_text = _format_spreads_for_llm(spreads)

        # Step 2: Generate character bibles from entity definitions
        entity_bibles = llm_retry(self.bible_generator)(
            title=title,
            story_text=story_text,
            entity_definitions=entity_definitions,
            debug=True,
        )

        # Step 3: Select illustration style
        story_summary = f"{title}. {story_text[:500]}..."
        style_result = llm_retry(self.style_selector)(
            story_summary=story_summary,
            available_styles=get_all_styles_for_selection(),
        )

        selected_style_name = style_result.selected_style.strip().lower()
        illustration_style = get_style_by_name(selected_style_name)

        print(f"DEBUG Selected style: {selected_style_name}", file=sys.stderr)

        # Build metadata for illustration (using entity_bibles, not character_bibles)
        metadata = StoryMetadata(
            title=title,
            entity_definitions=entity_definitions,
            entity_bibles=entity_bibles,
            illustration_style=illustration_style,
            style_rationale=style_result.style_rationale,
        )

        return GeneratedStory(
            title=title,
            goal=goal,
            metadata=metadata,
            spreads=spreads,
        )

    def generate_illustrated(
        self,
        goal: str,
        target_age_range: str = "4-7",
        use_image_qa: bool = True,
        max_image_attempts: int = 3,
        debug: bool = False,
        on_progress: callable = None,
    ) -> GeneratedStory:
        """
        Generate a complete illustrated children's story using Nano Banana Pro.

        Full pipeline:
        1. Generate story text (title + 12 spreads in one call)
        2. Extract characters and generate bibles
        3. Select illustration style
        4. Generate character reference portraits
        5. Generate 12 spread illustrations using reference images (with QA)

        Args:
            goal: The learning goal or theme for the story
            target_age_range: Target reader age range
            use_image_qa: If True, run QA on images and regenerate failures
            max_image_attempts: Max regeneration attempts per image
            debug: Print progress info
            on_progress: Optional callback(stage, detail, completed, total) for progress updates

        Returns:
            GeneratedStory with illustrations
        """
        import sys

        # Step 1-3: Generate the story text
        if debug:
            print("Step 1: Generating story text (12 spreads)...", file=sys.stderr)
        if on_progress:
            on_progress("outline", "Crafting your story...", None, None)

        story = self(
            goal=goal,
            target_age_range=target_age_range,
        )

        if on_progress:
            on_progress("spreads", "Story text complete", 1, 1)

        if debug and story.metadata.illustration_style:
            print(f"Selected illustration style: {story.metadata.illustration_style.name}", file=sys.stderr)
            print(f"  Rationale: {story.metadata.style_rationale}", file=sys.stderr)

        # Step 4: Generate character reference images
        num_characters = len(story.metadata.entity_bibles) or len(story.metadata.character_bibles)
        if debug:
            print(f"Step 2: Generating reference images for {num_characters} characters...", file=sys.stderr)

        sheet_generator = CharacterSheetGenerator()
        reference_sheets = sheet_generator.generate_for_story(
            outline=story.metadata,
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
                outline=story.metadata,
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
                outline=story.metadata,
                reference_sheets=reference_sheets,
                debug=debug,
                on_progress=on_progress,
            )

        story.is_illustrated = True

        if debug:
            illustrated_count = sum(1 for s in story.spreads if s.illustration_image)
            print(f"Done! {illustrated_count}/{len(story.spreads)} spreads illustrated.", file=sys.stderr)

        return story
