"""Unit tests for ImageQA and VLMJudge."""

import pytest
from unittest.mock import MagicMock, patch

from backend.core.modules.image_qa import ImageQA, QAVerdict, ImageQAResult
from backend.core.modules.vlm_judge import VLMJudge, DetailedCheckResult


class TestImageQAInstantiation:
    """Tests for ImageQA instantiation and basic functionality."""

    def test_image_qa_can_be_instantiated(self):
        """ImageQA should instantiate without errors."""
        qa = ImageQA()
        assert qa is not None
        assert qa.require_text_free is True
        assert qa.min_character_score == 4
        assert qa.min_scene_score == 3
        assert qa.max_attempts == 3

    def test_image_qa_with_custom_params(self):
        """ImageQA should accept custom parameters."""
        qa = ImageQA(
            require_text_free=False,
            min_character_score=3,
            min_scene_score=2,
            max_regeneration_attempts=5,
        )
        assert qa.require_text_free is False
        assert qa.min_character_score == 3
        assert qa.min_scene_score == 2
        assert qa.max_attempts == 5

    def test_vlm_judge_property_does_not_crash(self):
        """Accessing vlm_judge property should not raise TypeError.

        This is a regression test for a bug where ImageQA passed an
        invalid kwarg to VLMJudge.__init__.
        """
        qa = ImageQA()
        # This should not raise TypeError
        judge = qa.vlm_judge
        assert isinstance(judge, VLMJudge)


class TestVLMJudgeInstantiation:
    """Tests for VLMJudge instantiation."""

    def test_vlm_judge_default_model(self):
        """VLMJudge should use default model."""
        judge = VLMJudge()
        assert "gemini" in judge.model.lower() or "flash" in judge.model.lower()

    def test_vlm_judge_custom_model(self):
        """VLMJudge should accept custom model."""
        judge = VLMJudge(model="custom-model")
        assert judge.model == "custom-model"


class TestQAVerdict:
    """Tests for QA verdict enum."""

    def test_verdict_values(self):
        """QAVerdict should have expected values."""
        assert QAVerdict.PASS.value == "pass"
        assert QAVerdict.FAIL_HAS_TEXT.value == "fail_has_text"
        assert QAVerdict.FAIL_CHARACTER.value == "fail_character"
        assert QAVerdict.FAIL_COMPOSITION.value == "fail_composition"
        assert QAVerdict.FAIL_STYLE.value == "fail_style"


class TestDetailedCheckResult:
    """Tests for DetailedCheckResult dataclass."""

    def test_default_values(self):
        """DetailedCheckResult should have sensible defaults."""
        result = DetailedCheckResult()
        assert result.has_overlay_text is False
        assert result.text_free is True
        assert result.character_match_score == 5
        assert result.scene_accuracy_score == 5
        assert result.overall_pass is True
        assert result.issues == []
