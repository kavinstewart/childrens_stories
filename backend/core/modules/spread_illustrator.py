"""
Module for generating spread illustrations using Nano Banana Pro.

Uses character reference images and illustration prompts in multimodal
prompts to generate consistent illustrations for each spread of the story.

A spread = two facing pages when the book is open. A 32-page picture book
has 12 spreads of story content (after cover, title page, etc.).

Supports optional QA with automatic regeneration:
- Fast pass: VQAScore for prompt-image alignment
- Detailed pass: VLM check for text-free, character consistency, etc.
"""

import re
import sys
from typing import TYPE_CHECKING, Optional, Tuple

from backend.config import get_image_client, get_image_model, get_image_config, IMAGE_CONSTANTS, extract_image_from_response
from ..types import (
    StoryMetadata, StorySpread, StoryReferenceSheets,
    build_illustration_prompt, DEFAULT_LIGHTING,
    _normalize_name, _strip_leading_article, build_character_lookup, name_matches_in_text,
)

# Stopwords that should never be used for character matching
# These are common words that appear in text but are not character names
STOPWORDS = frozenset([
    "he", "she", "they", "him", "her", "his", "hers", "their", "theirs",
    "the", "a", "an", "in", "on", "at", "to", "of", "and", "or", "but",
    "is", "was", "are", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "it", "its", "this", "that", "these", "those", "with", "for", "from",
    "up", "down", "out", "into", "over", "under", "again", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "each", "every",
    "both", "few", "more", "most", "other", "some", "such", "no", "not",
    "only", "own", "same", "so", "than", "too", "very", "just", "now",
])

if TYPE_CHECKING:
    from .image_qa import ImageQAResult


class SpreadIllustrator:
    """
    Generate illustrations for story spreads using Nano Banana Pro.

    Generates 12 illustrations (one per spread) for a complete picture book.
    Uses character reference images as visual anchors in multimodal prompts
    to maintain consistency across all spread illustrations.
    """

    def __init__(self):
        self.client = get_image_client()
        self.model = get_image_model()
        self.config = get_image_config()

    def _build_scene_prompt(
        self,
        spread: StorySpread,
        outline: StoryMetadata,
    ) -> str:
        """
        Build scene prompt optimized for Nano Banana Pro.

        Follows Google's recommended practices:
        - Concise narrative description (not keyword lists)
        - Specific lighting and camera direction
        - Clear style specification without conflicts
        - Identity locking for character consistency
        """
        # Get style info (style is always set by StoryGenerator)
        if not outline.illustration_style:
            raise ValueError("illustration_style is required - StoryGenerator should always set this")

        style = outline.illustration_style
        return build_illustration_prompt(
            illustration_prompt=spread.illustration_prompt,
            setting=outline.setting,
            style_prefix=style.prompt_prefix,
            lighting=style.lighting_direction or DEFAULT_LIGHTING,
        )

    def illustrate_spread(
        self,
        spread: StorySpread,
        outline: StoryMetadata,
        reference_sheets: Optional[StoryReferenceSheets] = None,
        debug: bool = False,
        custom_prompt: Optional[str] = None,
    ) -> bytes:
        """
        Generate an illustration for a single spread using Nano Banana Pro.

        Uses multimodal prompting: passes all character reference images
        along with the scene description in a single API call.

        Args:
            spread: The story spread to illustrate
            outline: The story outline with character bibles
            reference_sheets: Character reference images for consistency
            debug: Print debug info
            custom_prompt: Optional custom prompt to use instead of building from template.
                          If provided, bypasses _build_scene_prompt entirely.

        Returns:
            PNG/JPEG image bytes
        """
        # Use custom prompt if provided, otherwise build from template
        if custom_prompt:
            scene_prompt = custom_prompt
        else:
            scene_prompt = self._build_scene_prompt(spread, outline)
        contents = self._build_contents(spread, outline, reference_sheets, scene_prompt)

        if debug:
            # Count reference images (every other item before the prompt is a ref image)
            num_refs = sum(1 for c in contents[:-1] if not isinstance(c, str))
            if num_refs > 0:
                print(f"  Using {num_refs} character reference images", file=sys.stderr)
            print(f"  Prompt length: {len(scene_prompt)} chars", file=sys.stderr)

        try:
            return self._generate_image(contents)
        except ValueError:
            raise ValueError(f"No image generated for spread {spread.spread_number}")

    def illustrate_story(
        self,
        spreads: list[StorySpread],
        outline: StoryMetadata,
        reference_sheets: Optional[StoryReferenceSheets] = None,
        debug: bool = False,
        on_progress: callable = None,
    ) -> list[StorySpread]:
        """
        Generate illustrations for all spreads in a story in parallel (typically 12).

        Args:
            spreads: List of story spreads
            outline: The story outline with character bibles
            reference_sheets: Character reference images
            debug: Print progress info
            on_progress: Optional callback(stage, detail, completed, total) for progress updates

        Returns:
            List of StorySpread objects with illustration_image populated
        """
        import concurrent.futures

        total_spreads = len(spreads)

        if on_progress:
            on_progress("illustrations", f"Generating {total_spreads} spread illustrations...", 0, total_spreads)

        def illustrate_one(spread):
            """Generate illustration for a single spread."""
            try:
                image_bytes = self.illustrate_spread(
                    spread=spread,
                    outline=outline,
                    reference_sheets=reference_sheets,
                    debug=False,  # Disable per-spread debug in parallel mode
                )
                return spread.spread_number, image_bytes, None
            except Exception as e:
                return spread.spread_number, None, e

        # Generate all spread illustrations in parallel
        # Use up to 6 workers to avoid overwhelming the API
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(total_spreads, 6)) as executor:
            futures = {executor.submit(illustrate_one, spread): spread for spread in spreads}

            completed = 0
            for future in concurrent.futures.as_completed(futures):
                spread_num, image_bytes, error = future.result()
                completed += 1

                # Find the spread and update it
                for spread in spreads:
                    if spread.spread_number == spread_num:
                        if image_bytes:
                            spread.illustration_image = image_bytes
                            if debug:
                                print(f"  Done ({completed}/{total_spreads}): Spread {spread_num} ({len(image_bytes)} bytes)", file=sys.stderr)
                        else:
                            spread.illustration_image = None
                            if debug:
                                print(f"  FAILED ({completed}/{total_spreads}): Spread {spread_num} - {error}", file=sys.stderr)
                        break

                if on_progress:
                    on_progress("illustrations", f"Illustrated spread {spread_num}", completed, total_spreads)

        # Final progress update
        if on_progress:
            on_progress("illustrations", "All illustrations complete", total_spreads, total_spreads)

        return spreads

    # === QA-ENABLED METHODS ===

    def _extract_character_names(self, text: str) -> list[str]:
        """
        Extract potential character names from text.

        Filters out stopwords and short tokens (< 3 chars) to avoid false matches.
        This is only used as a fallback when present_characters is not populated.
        """
        words = re.findall(r'\b[A-Z][a-z]+\b', text)
        # Filter out stopwords and tokens < 3 chars
        filtered = [
            w for w in words
            if len(w) >= 3 and w.lower() not in STOPWORDS
        ]
        return list(set(filtered))

    def _resolve_present_characters(
        self, present_characters: list[str], character_bibles: list
    ) -> list[str]:
        """
        Resolve present_characters names to canonical character bible names.

        Uses normalization and article-stripping for flexible matching.
        Unknown names are logged and skipped (no fuzzy/substring matching).

        Args:
            present_characters: List of character names from spread.present_characters
            character_bibles: List of CharacterBible objects

        Returns:
            List of canonical character names that were successfully resolved
        """
        lookup = build_character_lookup(character_bibles)
        resolved = []

        for name in present_characters:
            # Try normalized name
            normalized = _normalize_name(name)
            if normalized in lookup:
                resolved.append(lookup[normalized])
                continue

            # Try article-stripped version
            stripped = _strip_leading_article(name)
            if stripped in lookup:
                resolved.append(lookup[stripped])
                continue

            # Unknown character - log and skip (no fuzzy matching!)
            print(
                f"WARNING: Character '{name}' in present_characters not found in "
                f"character_bibles. Skipping. Known characters: "
                f"{[b.name for b in character_bibles]}",
                file=sys.stderr
            )

        return resolved

    def _get_characters_for_spread(self, spread: StorySpread, outline: StoryMetadata) -> list[str]:
        """
        Determine which characters should have reference images included for this spread.

        Priority:
        1. Use spread.present_characters if populated (from LLM [Characters:] field)
        2. Fall back to safe text-based detection (word-boundary matching only)

        Returns:
            List of canonical character names to include reference images for
        """
        # Priority 1: Use explicit present_characters if available
        if spread.present_characters is not None:
            return self._resolve_present_characters(
                spread.present_characters, outline.character_bibles
            )

        # Priority 2: Fallback to text-based detection with SAFE matching
        # WARNING: This path means [Characters:] was missing from story generation
        print(
            f"WARNING: Spread {spread.spread_number} has no present_characters. "
            "Falling back to text-based character detection. "
            "Consider regenerating story with [Characters:] field.",
            file=sys.stderr
        )

        combined_text = spread.illustration_prompt + ' ' + spread.text
        matched_characters = []

        for bible in outline.character_bibles:
            # Use safe word-boundary matching (NOT substring matching!)
            if name_matches_in_text(bible.name, combined_text):
                matched_characters.append(bible.name)

        return matched_characters

    def _build_contents(
        self,
        spread: StorySpread,
        outline: StoryMetadata,
        reference_sheets: Optional[StoryReferenceSheets],
        scene_prompt: str,
    ) -> list:
        """Build multimodal contents list for image generation.

        Uses spread.present_characters to determine which character reference
        sheets to include. Falls back to mention-based detection for backwards
        compatibility with stories that don't have present_characters populated.
        """
        contents = []

        # Add character reference images for characters present in this spread
        if reference_sheets and reference_sheets.character_sheets:
            # Get characters that should appear in this spread
            characters_in_spread = self._get_characters_for_spread(spread, outline)

            added_refs = 0
            max_refs = IMAGE_CONSTANTS["max_reference_images"]

            for char_name in characters_in_spread:
                if added_refs >= max_refs:
                    break

                # Find matching character bible and reference sheet
                bible = outline.get_character_bible(char_name)
                sheet = reference_sheets.get_sheet(char_name)

                if sheet and bible:
                    pil_image = sheet.to_pil_image()
                    contents.append(pil_image)
                    # Identity locking: explicit instruction to maintain exact features
                    contents.append(
                        f"CHARACTER REFERENCE for {bible.name}: Use this as strict visual reference. "
                        f"Maintain exact facial features, proportions, and clothing. {bible.to_prompt_string()}"
                    )
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

    def illustrate_spread_with_qa(
        self,
        spread: StorySpread,
        outline: StoryMetadata,
        reference_sheets: Optional[StoryReferenceSheets] = None,
        max_attempts: int = 3,
        debug: bool = False,
    ) -> Tuple[bytes, "ImageQAResult"]:
        """
        Generate illustration with QA loop for automatic regeneration.

        Args:
            spread: The story spread to illustrate
            outline: The story outline with character bibles
            reference_sheets: Character reference images for consistency
            max_attempts: Maximum regeneration attempts
            debug: Print debug info

        Returns:
            Tuple of (image_bytes, qa_result)
        """
        from .image_qa import ImageQA, QAVerdict

        qa = ImageQA(max_regeneration_attempts=max_attempts)
        prompt = self._build_scene_prompt(spread, outline)

        for attempt in range(1, max_attempts + 1):
            if debug:
                print(f"  Attempt {attempt}/{max_attempts}...", file=sys.stderr)

            # Build contents with current prompt
            contents = self._build_contents(spread, outline, reference_sheets, prompt)

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
                prompt=spread.illustration_prompt,  # Use original prompt for QA
                image_id=f"spread_{spread.spread_number:02d}",
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
                    print("    Max attempts reached, accepting with issues", file=sys.stderr)
                return image_bytes, qa_result

            # Get enhanced prompt for retry
            regen_request = qa.create_regeneration_request(qa_result)
            if regen_request:
                prompt = regen_request.enhanced_prompt
                if debug:
                    print("    Regenerating with enhanced prompt...", file=sys.stderr)

        # Return last attempt if all failed
        return image_bytes, qa_result

    def illustrate_story_with_qa(
        self,
        spreads: list[StorySpread],
        outline: StoryMetadata,
        reference_sheets: Optional[StoryReferenceSheets] = None,
        max_attempts_per_spread: int = 3,
        debug: bool = False,
        on_progress: callable = None,
    ) -> Tuple[list[StorySpread], dict]:
        """
        Generate illustrations for all spreads with QA in parallel (typically 12 images).

        Args:
            spreads: List of story spreads
            outline: The story outline with character bibles
            reference_sheets: Character reference images
            max_attempts_per_spread: Max regeneration attempts per spread
            debug: Print progress info
            on_progress: Optional callback(stage, detail, completed, total) for progress updates

        Returns:
            Tuple of (spreads with illustrations, qa_summary dict)
        """
        import concurrent.futures
        import threading
        from .image_qa import QAVerdict

        total_spreads = len(spreads)
        qa_summary = {
            "total_spreads": total_spreads,
            "passed": 0,
            "failed": 0,
            "total_attempts": 0,
            "regenerations": 0,
            "issues_by_type": {},
        }
        summary_lock = threading.Lock()

        if on_progress:
            on_progress("illustrations", f"Generating {total_spreads} spread illustrations with QA...", 0, total_spreads)

        def illustrate_one_with_qa(spread):
            """Generate illustration with QA for a single spread."""
            try:
                image_bytes, qa_result = self.illustrate_spread_with_qa(
                    spread=spread,
                    outline=outline,
                    reference_sheets=reference_sheets,
                    max_attempts=max_attempts_per_spread,
                    debug=False,  # Disable per-spread debug in parallel mode
                )
                return spread.spread_number, image_bytes, qa_result, None
            except Exception as e:
                return spread.spread_number, None, None, e

        # Generate all spread illustrations in parallel with QA
        # Use up to 6 workers to avoid overwhelming the API
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(total_spreads, 6)) as executor:
            futures = {executor.submit(illustrate_one_with_qa, spread): spread for spread in spreads}

            completed = 0
            for future in concurrent.futures.as_completed(futures):
                spread_num, image_bytes, qa_result, error = future.result()
                completed += 1

                # Find the spread and update it
                for spread in spreads:
                    if spread.spread_number == spread_num:
                        if image_bytes and qa_result:
                            spread.illustration_image = image_bytes

                            # Update summary (thread-safe)
                            with summary_lock:
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
                                print(f"  Done ({completed}/{total_spreads}): Spread {spread_num} - "
                                      f"{qa_result.verdict.value} (attempt {qa_result.attempt_number})", file=sys.stderr)
                        else:
                            spread.illustration_image = None
                            with summary_lock:
                                qa_summary["failed"] += 1
                            if debug:
                                print(f"  FAILED ({completed}/{total_spreads}): Spread {spread_num} - {error}", file=sys.stderr)
                        break

                if on_progress:
                    on_progress("illustrations", f"Illustrated spread {spread_num}", completed, total_spreads)

        # Final progress update
        if on_progress:
            on_progress("illustrations", "All illustrations complete", total_spreads, total_spreads)

        if debug:
            print("\nQA Summary:", file=sys.stderr)
            print(f"  Passed: {qa_summary['passed']}/{qa_summary['total_spreads']}", file=sys.stderr)
            print(f"  Regenerations: {qa_summary['regenerations']}", file=sys.stderr)
            if qa_summary["issues_by_type"]:
                print(f"  Issues: {qa_summary['issues_by_type']}", file=sys.stderr)

        return spreads, qa_summary
