"""
Module for generating character reference images using Nano Banana Pro.

Generates simple portrait references for each character to ensure
visual consistency across all story illustrations.
"""

import base64

from ..config import get_image_client, get_image_model, get_image_config
from ..types import (
    CharacterBible,
    StoryOutline,
    CharacterReferenceSheet,
    StoryReferenceSheets,
)


class CharacterSheetGenerator:
    """
    Generate character reference images using Nano Banana Pro.

    Creates simple portrait references that serve as visual anchors
    for consistent character appearance across all story illustrations.
    """

    def __init__(self):
        self.client = get_image_client()
        self.model = get_image_model()
        self.config = get_image_config()

    def _build_reference_prompt(self, bible: CharacterBible, illustration_style=None) -> str:
        """Build the prompt for generating a character model sheet with multiple views."""
        colors_str = ", ".join(bible.color_palette) if bible.color_palette else ""

        # Use illustration style if provided, otherwise fall back to character style tags
        if illustration_style:
            style_prefix = illustration_style.prompt_prefix
            style_suffix = illustration_style.prompt_suffix
        else:
            style_str = ", ".join(bible.style_tags) if bible.style_tags else "children's book illustration style"
            style_prefix = f"Character model sheet in {style_str}."
            style_suffix = ""

        prompt = f"""{style_prefix}

Generate a CHARACTER MODEL SHEET / TURNAROUND for a children's book character.

CHARACTER: {bible.name}
- Species/Type: {bible.species}
- Age: {bible.age_appearance}
- Body: {bible.body}
- Face: {bible.face}
- Hair: {bible.hair}
- Eyes: {bible.eyes}
- Clothing: {bible.clothing}
- Signature item: {bible.signature_item}

COLOR PALETTE: {colors_str}

{style_suffix}

MODEL SHEET LAYOUT - Include ALL of these views in a single image:
1. FRONT VIEW (full body, arms slightly away from body, neutral pose)
2. 3/4 VIEW (full body, showing depth and volume)
3. SIDE VIEW (profile, full body)
4. EXPRESSION SHEET (3-4 head shots showing: happy, sad, surprised, determined)

REQUIREMENTS:
- Clean white or light gray background
- All views of the SAME character with IDENTICAL design
- Clear, consistent proportions across all views
- Show full body in the turnaround views (head to feet)
- Character should be the focus - large and clearly visible
- Same clothing and accessories in every view
- No text, labels, or annotations
- Professional character design sheet layout

This model sheet will be used as reference to maintain character consistency across multiple story illustrations."""

        return prompt

    def generate_reference(self, bible: CharacterBible, illustration_style=None) -> CharacterReferenceSheet:
        """Generate a reference portrait for a character."""
        prompt = self._build_reference_prompt(bible, illustration_style)

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self.config,
        )

        # Extract image from response
        image_data = None
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                image_data = part.inline_data.data
                if isinstance(image_data, str):
                    image_data = base64.b64decode(image_data)
                break

        if not image_data:
            raise ValueError(f"No image generated for character: {bible.name}")

        # Build description for QA (age is critical for consistency checking)
        description = f"{bible.age_appearance}, {bible.species}, {bible.body}, {bible.face}"

        return CharacterReferenceSheet(
            character_name=bible.name,
            reference_image=image_data,
            prompt_used=prompt,
            character_description=description,
        )

    def generate_for_story(
        self,
        outline: StoryOutline,
        debug: bool = False,
    ) -> StoryReferenceSheets:
        """
        Generate reference images for all characters in a story.

        Args:
            outline: Story outline containing character bibles
            debug: Print progress info

        Returns:
            StoryReferenceSheets containing all character reference images
        """
        import sys

        sheets = StoryReferenceSheets(story_title=outline.title)

        # Use the illustration style from the outline
        illustration_style = outline.illustration_style

        if debug and illustration_style:
            print(f"Using illustration style: {illustration_style.name}", file=sys.stderr)

        for i, bible in enumerate(outline.character_bibles):
            if debug:
                print(f"Generating reference for character {i+1}/{len(outline.character_bibles)}: {bible.name}", file=sys.stderr)

            try:
                sheet = self.generate_reference(bible, illustration_style)
                sheets.character_sheets[bible.name] = sheet

                if debug:
                    print(f"  Done: {bible.name} ({len(sheet.reference_image)} bytes)", file=sys.stderr)

            except Exception as e:
                if debug:
                    print(f"  FAILED: {bible.name} - {e}", file=sys.stderr)

        return sheets
