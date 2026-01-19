"""
Module for generating character reference images using Nano Banana Pro.

Generates character model sheets (turnarounds) for each character to ensure
visual consistency across all story illustrations. Optimized for Nano Banana Pro
following Google's recommended prompting practices.
"""

from backend.config import get_image_client, get_image_model, get_image_config, extract_image_from_response, image_retry
from ..types import (
    CharacterBible,
    StoryMetadata,
    StyleDefinition,
    CharacterReferenceSheet,
    StoryReferenceSheets,
)


class CharacterSheetGenerator:
    """
    Generate character reference images using Nano Banana Pro.

    Creates model sheet turnarounds that serve as visual anchors
    for consistent character appearance across all story illustrations.
    """

    def __init__(self):
        self.client = get_image_client()
        self.model = get_image_model()
        self.config = get_image_config()

    def _build_reference_prompt(self, bible: CharacterBible, illustration_style: StyleDefinition) -> str:
        """
        Build concise prompt for character model sheet, optimized for Nano Banana Pro.

        Follows Google's recommended practices:
        - Concise narrative description
        - Specific lighting from style
        - Clear layout direction
        """
        colors_str = ", ".join(bible.color_palette) if bible.color_palette else "warm, appealing colors"
        lighting = illustration_style.lighting_direction or "soft even studio lighting"

        # Concise character description
        character_desc = f"{bible.age_appearance} {bible.species}, {bible.body}, {bible.face}"
        if bible.hair:
            character_desc += f", {bible.hair}"
        if bible.clothing:
            character_desc += f", wearing {bible.clothing}"
        if bible.signature_item:
            character_desc += f", with {bible.signature_item}"

        prompt = f"""{illustration_style.prompt_prefix}, character model sheet turnaround on clean white background.

Character: {bible.name} - {character_desc}.

Color palette: {colors_str}. Lighting: {lighting}.

Layout: Front view, 3/4 view, side profile (all full body), plus 4 expression head shots (happy, sad, surprised, determined). Identical character design across all views. No text or labels."""

        return prompt

    @image_retry
    def _generate_image(self, prompt: str) -> bytes:
        """Generate image from prompt with retry for network errors."""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self.config,
        )
        return extract_image_from_response(response)

    def generate_reference(
        self,
        bible: CharacterBible,
        illustration_style: StyleDefinition,
        entity_id: str = None,
    ) -> CharacterReferenceSheet:
        """Generate a character model sheet reference image.

        Args:
            bible: Character visual description
            illustration_style: Style to use for generation
            entity_id: Optional entity ID (e.g., "@e1") for new entity system

        Returns:
            CharacterReferenceSheet with generated image
        """
        if not illustration_style:
            raise ValueError("illustration_style is required")

        prompt = self._build_reference_prompt(bible, illustration_style)

        try:
            image_data = self._generate_image(prompt)
        except ValueError:
            raise ValueError(f"No image generated for character: {bible.name}")

        # Build description for QA (age is critical for consistency checking)
        description = f"{bible.age_appearance}, {bible.species}, {bible.body}, {bible.face}"

        return CharacterReferenceSheet(
            character_name=bible.name,
            reference_image=image_data,
            prompt_used=prompt,
            character_description=description,
            bible=bible,  # Store full bible for editing (story-37l6)
            entity_id=entity_id,  # Entity ID for new entity tagging system
        )

    def generate_for_story(
        self,
        outline: StoryMetadata,
        debug: bool = False,
        on_progress: callable = None,
    ) -> StoryReferenceSheets:
        """
        Generate reference images for all characters in a story (in parallel).

        Uses entity_bibles (new system, keyed by entity ID) if populated,
        otherwise falls back to character_bibles (legacy, keyed by name).

        Args:
            outline: Story outline containing character bibles
            debug: Print progress info
            on_progress: Optional callback(stage, detail, completed, total) for progress updates

        Returns:
            StoryReferenceSheets containing all character reference images
        """
        import sys
        import concurrent.futures

        sheets = StoryReferenceSheets(story_title=outline.title)

        # Use the illustration style from the outline
        illustration_style = outline.illustration_style

        # Check if using new entity_bibles system or legacy character_bibles
        use_entity_ids = bool(outline.entity_bibles)

        if use_entity_ids:
            # New system: entity_bibles is dict[entity_id, CharacterBible]
            bibles_to_generate = list(outline.entity_bibles.items())
            total_characters = len(bibles_to_generate)
        else:
            # Legacy: character_bibles is list[CharacterBible]
            bibles_to_generate = [(None, bible) for bible in outline.character_bibles]
            total_characters = len(bibles_to_generate)

        if total_characters == 0:
            if debug:
                print("No characters to generate references for", file=sys.stderr)
            return sheets

        if debug and illustration_style:
            print(f"Using illustration style: {illustration_style.name}", file=sys.stderr)

        if on_progress:
            on_progress("character_refs", f"Generating {total_characters} character references...", 0, total_characters)

        def generate_one(entity_id_and_bible):
            """Generate reference for a single character."""
            entity_id, bible = entity_id_and_bible
            try:
                sheet = self.generate_reference(bible, illustration_style, entity_id=entity_id)
                # Key by entity_id if available, otherwise by name
                key = entity_id if entity_id else bible.name
                return key, sheet, None
            except Exception as e:
                key = entity_id if entity_id else bible.name
                return key, None, e

        # Generate all character references in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(total_characters, 4)) as executor:
            futures = {executor.submit(generate_one, item): item for item in bibles_to_generate}

            completed = 0
            for future in concurrent.futures.as_completed(futures):
                key, sheet, error = future.result()
                completed += 1

                if sheet:
                    sheets.character_sheets[key] = sheet
                    if debug:
                        print(f"  Done ({completed}/{total_characters}): {key} ({len(sheet.reference_image)} bytes)", file=sys.stderr)
                else:
                    if debug:
                        print(f"  FAILED ({completed}/{total_characters}): {key} - {error}", file=sys.stderr)

                if on_progress:
                    on_progress("character_refs", f"Created {key}", completed, total_characters)

        # Final progress update
        if on_progress:
            on_progress("character_refs", "Character references complete", total_characters, total_characters)

        return sheets
