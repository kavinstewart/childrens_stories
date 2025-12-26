"""
Image QA module for children's book illustrations.

Uses VLM-based checking for text-free, character consistency, composition, and style.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Union, Optional
from PIL import Image
from io import BytesIO

from .vlm_judge import VLMJudge, DetailedCheckResult
from ..types import StoryReferenceSheets


class QAVerdict(Enum):
    """Possible QA verdicts for an image."""
    PASS = "pass"
    FAIL_HAS_TEXT = "fail_has_text"        # Image contains text
    FAIL_CHARACTER = "fail_character"       # Characters don't match refs
    FAIL_COMPOSITION = "fail_composition"   # Poor composition/scene accuracy
    FAIL_STYLE = "fail_style"              # Wrong style


@dataclass
class ImageQAResult:
    """Complete QA result for an image."""
    image_id: str              # e.g., "page_01" or "pepper_ref"
    prompt_used: str

    # VLM detailed check result
    detailed_check: Optional[DetailedCheckResult] = None

    # Final verdict
    verdict: QAVerdict = QAVerdict.PASS
    should_regenerate: bool = False
    failure_reasons: list[str] = field(default_factory=list)

    # Attempt tracking
    attempt_number: int = 1
    max_attempts: int = 3


@dataclass
class RegenerationRequest:
    """Request to regenerate an image with feedback."""
    image_id: str
    original_prompt: str
    failure_reasons: list[str]
    enhanced_prompt: str       # Original + "AVOID: {issues}"
    attempt_number: int


class ImageQA:
    """
    VLM-based image quality assurance for children's book illustrations.

    Checks for text-free images, character consistency, composition, and style.
    """

    def __init__(
        self,
        require_text_free: bool = True,
        min_character_score: int = 4,
        min_scene_score: int = 3,
        max_regeneration_attempts: int = 3,
    ):
        """
        Args:
            require_text_free: Whether to require no text in images (default True)
            min_character_score: Minimum character match score 1-5 (default 4)
            min_scene_score: Minimum scene accuracy score 1-5 (default 3)
            max_regeneration_attempts: Max retries before accepting (default 3)
        """
        self.require_text_free = require_text_free
        self.min_character_score = min_character_score
        self.min_scene_score = min_scene_score
        self.max_attempts = max_regeneration_attempts

        # Initialize VLM judge lazily
        self._vlm_judge = None

    @property
    def vlm_judge(self) -> VLMJudge:
        """Lazy load VLMJudge."""
        if self._vlm_judge is None:
            self._vlm_judge = VLMJudge()
        return self._vlm_judge

    def evaluate(
        self,
        image: Union[bytes, Image.Image],
        prompt: str,
        image_id: str = "unknown",
        reference_sheets: Optional[StoryReferenceSheets] = None,
        attempt_number: int = 1,
    ) -> ImageQAResult:
        """
        Run full QA evaluation on an image.

        Args:
            image: The generated image
            prompt: The generation prompt
            image_id: Identifier for logging (e.g., "page_01")
            reference_sheets: Character references for consistency check
            attempt_number: Current attempt (for tracking retries)

        Returns:
            ImageQAResult with verdict and any issues found
        """
        result = ImageQAResult(
            image_id=image_id,
            prompt_used=prompt,
            attempt_number=attempt_number,
            max_attempts=self.max_attempts,
        )

        # Convert to PIL if needed
        if isinstance(image, bytes):
            pil_image = Image.open(BytesIO(image))
        else:
            pil_image = image

        # Ensure RGB
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")

        # === VLM Check ===
        character_refs = None
        if reference_sheets:
            # Use descriptions for better age/feature checking
            character_refs = reference_sheets.get_all_with_descriptions()

        result.detailed_check = self.vlm_judge.evaluate(
            image=pil_image,
            prompt=prompt,
            character_refs=character_refs,
            check_text_free=self.require_text_free,
            check_characters=bool(character_refs),
            check_composition=True,
        )

        # Check for failures
        dc = result.detailed_check

        # Text-free check (highest priority for children's books)
        if self.require_text_free and not dc.text_free:
            result.verdict = QAVerdict.FAIL_HAS_TEXT
            result.failure_reasons.append(f"Text detected in image: {dc.text_detected}")
            result.should_regenerate = attempt_number < self.max_attempts
            return result

        # Character consistency check
        if dc.character_match_score < self.min_character_score:
            result.verdict = QAVerdict.FAIL_CHARACTER
            result.failure_reasons.extend(dc.character_issues)
            if not result.failure_reasons:
                result.failure_reasons.append(f"Character match score {dc.character_match_score}/5 below minimum {self.min_character_score}")
            result.should_regenerate = attempt_number < self.max_attempts
            return result

        # Scene accuracy check
        if dc.scene_accuracy_score < self.min_scene_score:
            result.verdict = QAVerdict.FAIL_COMPOSITION
            result.failure_reasons.extend(dc.scene_issues)
            if not result.failure_reasons:
                result.failure_reasons.append(f"Scene accuracy score {dc.scene_accuracy_score}/5 below minimum {self.min_scene_score}")
            result.should_regenerate = attempt_number < self.max_attempts
            return result

        # Overall pass from VLM
        if not dc.overall_pass:
            result.verdict = QAVerdict.FAIL_STYLE
            result.failure_reasons.extend(dc.issues)
            result.should_regenerate = attempt_number < self.max_attempts
            return result

        # All checks passed
        result.verdict = QAVerdict.PASS
        result.should_regenerate = False
        return result

    def create_regeneration_request(
        self,
        qa_result: ImageQAResult,
    ) -> Optional[RegenerationRequest]:
        """
        Create a regeneration request with enhanced prompt based on failures.

        Args:
            qa_result: The failed QA result

        Returns:
            RegenerationRequest with enhanced prompt, or None if shouldn't regenerate
        """
        if not qa_result.should_regenerate:
            return None

        # Build enhanced prompt with failure avoidance
        avoid_instructions = []

        if qa_result.verdict == QAVerdict.FAIL_HAS_TEXT:
            avoid_instructions.append(
                "CRITICAL: Do NOT include ANY text, words, letters, numbers, "
                "signs, labels, speech bubbles, or writing of any kind in the image. "
                "If showing a sign or book, make it blank or illegible."
            )

        if qa_result.verdict == QAVerdict.FAIL_CHARACTER:
            issues_str = "; ".join(qa_result.failure_reasons) if qa_result.failure_reasons else "characters don't match references"
            avoid_instructions.append(
                f"FIX CHARACTER ISSUES: {issues_str}. "
                "Ensure characters exactly match the reference images provided."
            )

        if qa_result.verdict == QAVerdict.FAIL_COMPOSITION:
            issues_str = "; ".join(qa_result.failure_reasons) if qa_result.failure_reasons else "composition issues"
            avoid_instructions.append(
                f"FIX COMPOSITION: {issues_str}. "
                "Ensure proper layout with space for text and clear focal point."
            )

        if qa_result.verdict == QAVerdict.FAIL_STYLE:
            issues_str = "; ".join(qa_result.failure_reasons) if qa_result.failure_reasons else "style issues"
            avoid_instructions.append(
                f"FIX STYLE: {issues_str}. "
                "Use warm, child-friendly illustration style."
            )

        enhanced_prompt = qa_result.prompt_used
        if avoid_instructions:
            enhanced_prompt = (
                f"{qa_result.prompt_used}\n\n"
                f"IMPORTANT - AVOID THESE ISSUES FROM PREVIOUS ATTEMPT:\n"
                + "\n".join(f"- {instr}" for instr in avoid_instructions)
            )

        return RegenerationRequest(
            image_id=qa_result.image_id,
            original_prompt=qa_result.prompt_used,
            failure_reasons=qa_result.failure_reasons,
            enhanced_prompt=enhanced_prompt,
            attempt_number=qa_result.attempt_number + 1,
        )
