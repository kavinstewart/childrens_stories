"""
Module for generating page illustrations using Nano Banana Pro.

Uses character reference images and illustration prompts in multimodal
prompts to generate consistent illustrations for each page of the story.

Supports optional QA with automatic regeneration:
- Fast pass: VQAScore for prompt-image alignment
- Detailed pass: VLM check for text-free, character consistency, etc.
"""

import re
from typing import Optional, Tuple

from backend.config import get_image_client, get_image_model, get_image_config, IMAGE_CONSTANTS, extract_image_from_response
from ..types import StoryOutline, StoryPage, StoryReferenceSheets


class PageIllustrator:
    """
    Generate illustrations for story pages using Nano Banana Pro.

    Uses character reference images as visual anchors in multimodal prompts
    to maintain consistency across all page illustrations.
    """

    def __init__(self):
        self.client = get_image_client()
        self.model = get_image_model()
        self.config = get_image_config()

    def _extract_character_names(self, text: str) -> list[str]:
        """Extract character names mentioned in text."""
        # Simple extraction - looks for capitalized words that might be names
        words = re.findall(r'\b[A-Z][a-z]+\b', text)
        return list(set(words))

    def _build_scene_prompt(
        self,
        page: StoryPage,
        outline: StoryOutline,
    ) -> str:
        """Build the scene description part of the prompt."""
        # Use selected illustration style if available
        if outline.illustration_style:
            style = outline.illustration_style
            prompt = f"""{style.prompt_prefix}

Generate illustration for Page {page.page_number}.

SCENE DESCRIPTION:
{page.illustration_prompt}

STORY TEXT FOR THIS PAGE:
"{page.text}"

SETTING: {outline.setting}

{style.prompt_suffix}

ADDITIONAL REQUIREMENTS:
- Single cohesive illustration suitable for a picture book page
- Leave space for text (typically top or bottom 20% of image)
- Characters should be expressive and appealing to children
- Clear focal point as described in the scene
- Age-appropriate content
- No text or words in the image
- IMPORTANT: Characters must match the reference images provided above exactly"""
        else:
            # Fallback to old style if no illustration style selected
            style_tags = outline.get_all_style_tags()
            style_str = ", ".join(style_tags) if style_tags else "children's book illustration, warm colors, soft lighting"

            prompt = f"""Generate a children's picture book illustration for Page {page.page_number}.

SCENE DESCRIPTION:
{page.illustration_prompt}

STORY TEXT FOR THIS PAGE:
"{page.text}"

SETTING: {outline.setting}

STYLE: {style_str}

REQUIREMENTS:
- Single cohesive illustration suitable for a picture book page
- Leave space for text (typically top or bottom 20% of image)
- Characters should be expressive and appealing to children
- Warm, inviting color palette
- Clear focal point as described in the scene
- Age-appropriate content
- No text or words in the image
- IMPORTANT: Characters must match the reference images provided above exactly"""

        return prompt

    def illustrate_page(
        self,
        page: StoryPage,
        outline: StoryOutline,
        reference_sheets: Optional[StoryReferenceSheets] = None,
        debug: bool = False,
    ) -> bytes:
        """
        Generate an illustration for a single page using Nano Banana Pro.

        Uses multimodal prompting: passes all character reference images
        along with the scene description in a single API call.

        Args:
            page: The story page to illustrate
            outline: The story outline with character bibles
            reference_sheets: Character reference images for consistency
            debug: Print debug info

        Returns:
            PNG/JPEG image bytes
        """
        import sys

        scene_prompt = self._build_scene_prompt(page, outline)
        contents = self._build_contents(page, outline, reference_sheets, scene_prompt)

        if debug:
            # Count reference images (every other item before the prompt is a ref image)
            num_refs = sum(1 for c in contents[:-1] if not isinstance(c, str))
            if num_refs > 0:
                print(f"  Using {num_refs} character reference images", file=sys.stderr)
            print(f"  Prompt length: {len(scene_prompt)} chars", file=sys.stderr)

        try:
            return self._generate_image(contents)
        except ValueError:
            raise ValueError(f"No image generated for page {page.page_number}")

    def illustrate_story(
        self,
        pages: list[StoryPage],
        outline: StoryOutline,
        reference_sheets: Optional[StoryReferenceSheets] = None,
        debug: bool = False,
    ) -> list[StoryPage]:
        """
        Generate illustrations for all pages in a story.

        Args:
            pages: List of story pages
            outline: The story outline with character bibles
            reference_sheets: Character reference images
            debug: Print progress info

        Returns:
            List of StoryPage objects with illustration_image populated
        """
        import sys

        for i, page in enumerate(pages):
            if debug:
                print(f"Illustrating page {page.page_number} of {len(pages)}...", file=sys.stderr)

            try:
                image_bytes = self.illustrate_page(
                    page=page,
                    outline=outline,
                    reference_sheets=reference_sheets,
                    debug=debug,
                )
                page.illustration_image = image_bytes

                if debug:
                    print(f"  Page {page.page_number}: Generated {len(image_bytes)} bytes", file=sys.stderr)

            except Exception as e:
                if debug:
                    print(f"  Page {page.page_number}: FAILED - {e}", file=sys.stderr)
                page.illustration_image = None

        return pages

    # === QA-ENABLED METHODS ===

    def _build_contents(
        self,
        page: StoryPage,
        outline: StoryOutline,
        reference_sheets: Optional[StoryReferenceSheets],
        scene_prompt: str,
    ) -> list:
        """Build multimodal contents list for image generation."""
        contents = []

        # Add character reference images first (if available)
        if reference_sheets and reference_sheets.character_sheets:
            # Get character names mentioned in this page
            mentioned_names = self._extract_character_names(
                page.illustration_prompt + " " + page.text
            )

            # Add reference images for mentioned characters
            added_refs = 0
            max_refs = IMAGE_CONSTANTS["max_reference_images"]

            for bible in outline.character_bibles:
                is_mentioned = any(
                    name.lower() in bible.name.lower()
                    for name in mentioned_names
                )

                if is_mentioned or added_refs < 3:
                    sheet = reference_sheets.get_sheet(bible.name)
                    if sheet and added_refs < max_refs:
                        pil_image = sheet.to_pil_image()
                        contents.append(pil_image)
                        contents.append(f"This is {bible.name} - {bible.to_prompt_string()}")
                        added_refs += 1

        contents.append(scene_prompt)
        return contents

    def _generate_image(self, contents: list) -> bytes:
        """Generate image from multimodal contents."""
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=self.config,
        )
        return extract_image_from_response(response)

    def illustrate_page_with_qa(
        self,
        page: StoryPage,
        outline: StoryOutline,
        reference_sheets: Optional[StoryReferenceSheets] = None,
        max_attempts: int = 3,
        debug: bool = False,
    ) -> Tuple[bytes, "ImageQAResult"]:
        """
        Generate illustration with QA loop for automatic regeneration.

        Args:
            page: The story page to illustrate
            outline: The story outline with character bibles
            reference_sheets: Character reference images for consistency
            max_attempts: Maximum regeneration attempts
            debug: Print debug info

        Returns:
            Tuple of (image_bytes, qa_result)
        """
        import sys
        from .image_qa import ImageQA, QAVerdict

        qa = ImageQA(max_regeneration_attempts=max_attempts)
        prompt = self._build_scene_prompt(page, outline)

        for attempt in range(1, max_attempts + 1):
            if debug:
                print(f"  Attempt {attempt}/{max_attempts}...", file=sys.stderr)

            # Build contents with current prompt
            contents = self._build_contents(page, outline, reference_sheets, prompt)

            # Generate image
            try:
                image_bytes = self._generate_image(contents)
            except Exception as e:
                if debug:
                    print(f"    Generation failed: {e}", file=sys.stderr)
                continue

            # Run QA
            qa_result = qa.evaluate(
                image=image_bytes,
                prompt=page.illustration_prompt,  # Use original prompt for QA
                image_id=f"page_{page.page_number:02d}",
                reference_sheets=reference_sheets,
                attempt_number=attempt,
            )

            if debug:
                print(f"    Verdict: {qa_result.verdict.value}", file=sys.stderr)
                if qa_result.failure_reasons:
                    print(f"    Issues: {qa_result.failure_reasons}", file=sys.stderr)

            # Check if passed
            if qa_result.verdict == QAVerdict.PASS:
                return image_bytes, qa_result

            # Check if should regenerate
            if not qa_result.should_regenerate:
                if debug:
                    print(f"    Max attempts reached, accepting with issues", file=sys.stderr)
                return image_bytes, qa_result

            # Get enhanced prompt for retry
            regen_request = qa.create_regeneration_request(qa_result)
            if regen_request:
                prompt = regen_request.enhanced_prompt
                if debug:
                    print(f"    Regenerating with enhanced prompt...", file=sys.stderr)

        # Return last attempt if all failed
        return image_bytes, qa_result

    def illustrate_story_with_qa(
        self,
        pages: list[StoryPage],
        outline: StoryOutline,
        reference_sheets: Optional[StoryReferenceSheets] = None,
        max_attempts_per_page: int = 3,
        debug: bool = False,
    ) -> Tuple[list[StoryPage], dict]:
        """
        Generate illustrations for all pages with QA.

        Args:
            pages: List of story pages
            outline: The story outline with character bibles
            reference_sheets: Character reference images
            max_attempts_per_page: Max regeneration attempts per page
            debug: Print progress info

        Returns:
            Tuple of (pages with illustrations, qa_summary dict)
        """
        import sys
        from .image_qa import QAVerdict

        qa_summary = {
            "total_pages": len(pages),
            "passed": 0,
            "failed": 0,
            "total_attempts": 0,
            "regenerations": 0,
            "issues_by_type": {},
        }

        for i, page in enumerate(pages):
            if debug:
                print(f"Illustrating page {page.page_number} of {len(pages)}...", file=sys.stderr)

            try:
                image_bytes, qa_result = self.illustrate_page_with_qa(
                    page=page,
                    outline=outline,
                    reference_sheets=reference_sheets,
                    max_attempts=max_attempts_per_page,
                    debug=debug,
                )
                page.illustration_image = image_bytes

                # Update summary
                qa_summary["total_attempts"] += qa_result.attempt_number
                if qa_result.attempt_number > 1:
                    qa_summary["regenerations"] += qa_result.attempt_number - 1

                if qa_result.verdict == QAVerdict.PASS:
                    qa_summary["passed"] += 1
                else:
                    qa_summary["failed"] += 1
                    verdict_type = qa_result.verdict.value
                    qa_summary["issues_by_type"][verdict_type] = (
                        qa_summary["issues_by_type"].get(verdict_type, 0) + 1
                    )

                if debug:
                    print(f"  Page {page.page_number}: {qa_result.verdict.value} "
                          f"(attempt {qa_result.attempt_number})", file=sys.stderr)

            except Exception as e:
                if debug:
                    print(f"  Page {page.page_number}: FAILED - {e}", file=sys.stderr)
                page.illustration_image = None
                qa_summary["failed"] += 1

        if debug:
            print(f"\nQA Summary:", file=sys.stderr)
            print(f"  Passed: {qa_summary['passed']}/{qa_summary['total_pages']}", file=sys.stderr)
            print(f"  Regenerations: {qa_summary['regenerations']}", file=sys.stderr)
            if qa_summary["issues_by_type"]:
                print(f"  Issues: {qa_summary['issues_by_type']}", file=sys.stderr)

        return pages, qa_summary
