"""
Hybrid Image QA module for children's book illustrations.

Two-pass system:
1. Fast pass: VQAScore for prompt-image alignment (~$0.001, ~200ms)
2. Detailed pass: VLM check for text-free, character consistency, etc. (~$0.01, ~2-3s)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Union, Optional
from PIL import Image
from io import BytesIO

from .qa_metrics.vlm_judge import VLMJudge, DetailedCheckResult
from .character_sheet_generator import StoryReferenceSheets

# Try to import VQAScore - it has heavy dependencies that may not be available
try:
    from .qa_metrics.vqa_scorer import VQAScorer, FastPassResult
    VQA_AVAILABLE = True
except ImportError as e:
    VQA_AVAILABLE = False
    VQAScorer = None
    # Provide a stub FastPassResult for when VQA is unavailable
    @dataclass
    class FastPassResult:
        vqa_score: float
        passed: bool
        threshold_used: float


class QAVerdict(Enum):
    """Possible QA verdicts for an image."""
    PASS = "pass"
    FAIL_ALIGNMENT = "fail_alignment"      # VQAScore too low
    FAIL_HAS_TEXT = "fail_has_text"        # Image contains text
    FAIL_CHARACTER = "fail_character"       # Characters don't match refs
    FAIL_COMPOSITION = "fail_composition"   # Poor composition/scene accuracy
    FAIL_STYLE = "fail_style"              # Wrong style


@dataclass
class ImageQAResult:
    """Complete QA result for an image."""
    image_id: str              # e.g., "page_01" or "pepper_ref"
    prompt_used: str

    # Fast pass
    fast_pass: FastPassResult

    # Detailed pass (only if fast pass succeeded)
    detailed_check: Optional[DetailedCheckResult] = None

    # Final verdict
    verdict: QAVerdict = QAVerdict.PASS
    should_regenerate: bool = False
    failure_reasons: list[str] = field(default_factory=list)

    # Attempt tracking
    attempt_number: int = 1
    max_attempts: int = 3

    def get_summary(self) -> str:
        """Get a human-readable summary of the QA result."""
        lines = [
            f"Image: {self.image_id}",
            f"Verdict: {self.verdict.value}",
            f"VQAScore: {self.fast_pass.vqa_score:.2f} (threshold: {self.fast_pass.threshold_used})",
        ]

        if self.detailed_check:
            dc = self.detailed_check
            lines.extend([
                f"Text-free: {dc.text_free}" + (f" ({dc.text_detected})" if not dc.text_free else ""),
                f"Character match: {dc.character_match_score}/5",
                f"Scene accuracy: {dc.scene_accuracy_score}/5",
                f"Composition: {dc.composition_score}/5",
                f"Style: {dc.style_score}/5",
            ])

        if self.failure_reasons:
            lines.append(f"Issues: {'; '.join(self.failure_reasons)}")

        lines.append(f"Attempt: {self.attempt_number}/{self.max_attempts}")

        return "\n".join(lines)


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
    Hybrid image quality assurance for children's book illustrations.

    Two-pass system:
    1. Fast pass: VQAScore for prompt-image alignment
    2. Detailed pass: VLM check for text-free, character consistency, etc.
    """

    def __init__(
        self,
        vqa_threshold: float = 0.7,
        require_text_free: bool = True,
        min_character_score: int = 4,
        min_scene_score: int = 3,
        max_regeneration_attempts: int = 3,
        use_gpu: bool = True,
    ):
        """
        Args:
            vqa_threshold: Minimum VQAScore to pass fast check (default 0.7)
            require_text_free: Whether to require no text in images (default True)
            min_character_score: Minimum character match score 1-5 (default 4)
            min_scene_score: Minimum scene accuracy score 1-5 (default 3)
            max_regeneration_attempts: Max retries before accepting (default 3)
            use_gpu: Whether to use GPU for VQAScore (default True)
        """
        self.vqa_threshold = vqa_threshold
        self.require_text_free = require_text_free
        self.min_character_score = min_character_score
        self.min_scene_score = min_scene_score
        self.max_attempts = max_regeneration_attempts
        self._use_gpu = use_gpu

        # Initialize scorers lazily
        self._vqa_scorer = None
        self._vlm_judge = None

    @property
    def vqa_scorer(self) -> Optional[VQAScorer]:
        """Lazy load VQAScorer (returns None if unavailable)."""
        if not VQA_AVAILABLE:
            return None
        if self._vqa_scorer is None:
            device = "cuda" if self._use_gpu else "cpu"
            self._vqa_scorer = VQAScorer(model_name="clip-flant5-xl", device=device)
        return self._vqa_scorer

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
            fast_pass=FastPassResult(0.0, False, self.vqa_threshold),
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

        # === FAST PASS: VQAScore (if available) ===
        vqa_ran = False
        if VQA_AVAILABLE:
            try:
                result.fast_pass = self.vqa_scorer.check(
                    image=pil_image,
                    prompt=prompt,
                    threshold=self.vqa_threshold,
                )
                vqa_ran = True

                if not result.fast_pass.passed:
                    result.verdict = QAVerdict.FAIL_ALIGNMENT
                    result.should_regenerate = attempt_number < self.max_attempts
                    result.failure_reasons.append(
                        f"VQAScore {result.fast_pass.vqa_score:.2f} below threshold {self.vqa_threshold}"
                    )
                    return result
            except (ImportError, RuntimeError) as e:
                # VQA dependencies not working - fall back to VLM only
                pass

        if not vqa_ran:
            # VQA unavailable - mark as passed and rely on VLM check
            result.fast_pass = FastPassResult(
                vqa_score=-1.0,  # Indicates VQA was skipped
                passed=True,
                threshold_used=self.vqa_threshold,
            )

        # === DETAILED PASS: VLM Check ===
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

        if qa_result.verdict == QAVerdict.FAIL_ALIGNMENT:
            avoid_instructions.append(
                f"Ensure the image closely matches the scene description. "
                f"Previous attempt scored {qa_result.fast_pass.vqa_score:.2f}/1.0 on alignment - "
                "focus on including all described elements."
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
