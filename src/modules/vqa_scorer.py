"""
VQAScore wrapper for fast image-prompt alignment checking.

Uses CLIP-FlanT5 to answer "Does this image show {prompt}?" and returns P(Yes).
"""

from dataclasses import dataclass
from typing import Union
from PIL import Image
from io import BytesIO


@dataclass
class FastPassResult:
    """Result from VQAScore fast pass."""
    vqa_score: float           # 0.0 - 1.0
    passed: bool
    threshold_used: float


class VQAScorer:
    """
    Fast alignment scoring using VQAScore (CLIP-FlanT5).

    Answers: "Does this image show {prompt}?" → P(Yes)

    Industry standard as of 2025, used by Google DeepMind (Imagen 3 & 4),
    ByteDance Seed, NVIDIA.
    """

    def __init__(self, model_name: str = "clip-flant5-xl", device: str = "auto"):
        """
        Args:
            model_name: One of "clip-flant5-xl" (faster) or "clip-flant5-xxl" (better)
            device: "cuda", "cpu", or "auto"
        """
        self.model_name = model_name
        self.device = device
        self._scorer = None

    @property
    def scorer(self):
        """Lazy load the scorer model."""
        if self._scorer is None:
            from t2v_metrics import VQAScore

            device = self.device
            if device == "auto":
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"

            self._scorer = VQAScore(model=self.model_name, device=device)
        return self._scorer

    def score(
        self,
        image: Union[bytes, Image.Image, str],
        prompt: str
    ) -> float:
        """
        Score image-prompt alignment.

        Args:
            image: Image bytes, PIL Image, or file path
            prompt: The text prompt to check against

        Returns:
            Score from 0.0 to 1.0 (higher = better alignment)
        """
        # Convert bytes to PIL if needed
        if isinstance(image, bytes):
            image = Image.open(BytesIO(image))
        elif isinstance(image, str):
            image = Image.open(image)

        # Ensure RGB
        if image.mode != "RGB":
            image = image.convert("RGB")

        score = self.scorer(images=[image], texts=[prompt])
        return float(score[0])

    def check(
        self,
        image: Union[bytes, Image.Image, str],
        prompt: str,
        threshold: float = 0.7
    ) -> FastPassResult:
        """
        Check if image passes alignment threshold.

        Args:
            image: Image bytes, PIL Image, or file path
            prompt: The text prompt to check against
            threshold: Minimum score to pass (default 0.7)

        Returns:
            FastPassResult with score and pass/fail status
        """
        score = self.score(image, prompt)
        return FastPassResult(
            vqa_score=score,
            passed=score >= threshold,
            threshold_used=threshold
        )
