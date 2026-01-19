"""
DSPy Module for judging story quality.
"""

import dspy

from ..types import QualityJudgment
from ..signatures.story_judge import StoryJudgeSignature


class QualityJudge(dspy.Module):
    """
    Judge the quality of a children's story.

    Uses LLM-as-judge pattern with STRICT criteria.
    A story with missing pages or rhyming-only dialogue gets REJECTED.
    """

    def __init__(self):
        super().__init__()
        self.judge = dspy.ChainOfThought(StoryJudgeSignature)

    def _check_for_missing_pages(self, story_text: str) -> bool:
        """Pre-check for missing pages before LLM evaluation."""
        return "[generation failed]" in story_text.lower() or "generation failed" in story_text.lower()

    def forward(
        self,
        story_text: str,
        original_goal: str,
        target_age_range: str = "4-7",
    ) -> QualityJudgment:
        """
        Judge the quality of a story.

        Args:
            story_text: The complete story text
            original_goal: The original learning goal
            target_age_range: Target reader age range

        Returns:
            QualityJudgment dataclass with scores and feedback
        """
        # Pre-check for obvious failures
        has_missing_pages = self._check_for_missing_pages(story_text)

        result = self.judge(
            story_text=story_text,
            original_goal=original_goal,
            target_age_range=target_age_range,
        )

        # Parse scores (ensure they're integers)
        def parse_score(val, default=5):
            try:
                score = int(str(val).strip())
                return max(1, min(10, score))  # Clamp to 1-10
            except (ValueError, TypeError):
                return default

        def parse_bool(val):
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() in ("true", "yes", "1")
            return False

        has_critical = parse_bool(result.has_critical_failures)

        # Override if we detected missing pages
        if has_missing_pages:
            has_critical = True
            critical_reasons = f"Missing or failed page generation detected. {result.critical_failure_reasons or ''}"
        else:
            critical_reasons = result.critical_failure_reasons or "None"

        overall = parse_score(result.overall_score)

        # Enforce critical failure scoring
        if has_critical and overall > 2:
            overall = 2  # Cap at 2 for critical failures

        # Determine verdict based on score
        if overall <= 3 or has_critical:
            verdict = "REJECTED"
        elif overall <= 5:
            verdict = "NEEDS_WORK"
        elif overall <= 7:
            verdict = "GOOD"
        else:
            verdict = "EXCELLENT"

        # Parse chekhov fields
        chekhov_violations = getattr(result, 'chekhov_violations', '') or ""
        chekhov_score = parse_score(getattr(result, 'chekhov_score', 5))

        # If severe chekhov violations, treat as critical failure
        if chekhov_score <= 3 and chekhov_violations.lower() != "none":
            has_critical = True
            critical_reasons = f"{critical_reasons}\nChekhov's Gun violations: {chekhov_violations}"
            if overall > 3:
                overall = 3  # Cap score for coherence failures

        return QualityJudgment(
            has_critical_failures=has_critical,
            critical_failure_reasons=critical_reasons,
            engagement_score=parse_score(result.engagement_score),
            read_aloud_score=parse_score(result.read_aloud_score),
            emotional_truth_score=parse_score(result.emotional_truth_score),
            coherence_score=parse_score(result.coherence_score),
            chekhov_violations=chekhov_violations,
            chekhov_score=chekhov_score,
            overall_score=overall,
            specific_problems=result.specific_problems or "",
            verdict=verdict,
        )
