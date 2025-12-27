"""
VLM-as-Judge wrapper for detailed image evaluation.

Uses Gemini 3.0 Flash to check specific criteria:
- Text-free verification
- Character consistency with references
- Scene accuracy and composition

Supports optional logging of evaluations for GEPA optimization.
"""

import json
from dataclasses import dataclass, field
from typing import Union, Optional, TYPE_CHECKING
from PIL import Image
from io import BytesIO

from backend.config import get_image_client

if TYPE_CHECKING:
    from backend.api.database.vlm_eval_repository import VLMEvalRepository


@dataclass
class DetailedCheckResult:
    """Result from VLM detailed check."""
    text_free: bool = True             # No text/words in image
    text_detected: str = "none"        # Description of any text found
    character_match_score: int = 5     # 1-5
    character_issues: list[str] = field(default_factory=list)
    scene_accuracy_score: int = 5      # 1-5
    scene_issues: list[str] = field(default_factory=list)
    composition_score: int = 5         # 1-5
    style_score: int = 5               # 1-5
    overall_pass: bool = True
    issues: list[str] = field(default_factory=list)


class VLMJudge:
    """
    Detailed image evaluation using VLM (Gemini 3.0 Flash).

    Checks specific criteria that VQAScore might miss:
    - Text-free verification (critical for children's books)
    - Character consistency with reference images
    - Scene accuracy and composition
    """

    def __init__(self, model: str = "gemini-3.0-flash", enable_logging: bool = False):
        self.model = model
        self.enable_logging = enable_logging
        self._client = None

    @property
    def client(self):
        """Lazy load the client."""
        if self._client is None:
            self._client = get_image_client()
        return self._client

    def evaluate(
        self,
        image: Union[bytes, Image.Image],
        prompt: str,
        character_refs: Optional[list[tuple[str, Image.Image, str]]] = None,
        check_text_free: bool = True,
        check_characters: bool = True,
        check_composition: bool = True,
        story_id: Optional[str] = None,
        spread_number: Optional[int] = None,
    ) -> DetailedCheckResult:
        """
        Run detailed VLM evaluation on an image.

        Args:
            image: The generated image to evaluate
            prompt: The original generation prompt
            character_refs: List of (name, reference_image, description) tuples
            check_text_free: Whether to check for text in image
            check_characters: Whether to check character consistency
            check_composition: Whether to check composition/style
            story_id: Optional story ID for logging context
            spread_number: Optional spread number for logging context

        Returns:
            DetailedCheckResult with scores and issues
        """
        # Convert bytes to PIL if needed
        if isinstance(image, bytes):
            image = Image.open(BytesIO(image))

        # Ensure RGB
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Build evaluation prompt
        contents = []

        # Add character references if checking consistency
        if check_characters and character_refs:
            for ref in character_refs:
                # Handle both old (name, img) and new (name, img, desc) formats
                if len(ref) == 3:
                    name, ref_img, description = ref
                else:
                    name, ref_img = ref
                    description = ""
                if ref_img.mode != "RGB":
                    ref_img = ref_img.convert("RGB")
                contents.append(ref_img)
                desc_text = f" - MUST MATCH: {description}" if description else ""
                contents.append(f"Reference image for character: {name}{desc_text}")

        # Add the image to evaluate
        contents.append(image)
        contents.append(self._build_evaluation_prompt(
            prompt=prompt,
            check_text_free=check_text_free,
            check_characters=check_characters and bool(character_refs),
            check_composition=check_composition,
        ))

        # Call VLM
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
        )

        # Parse response
        raw_response = response.text
        result = self._parse_response(raw_response)

        # Log evaluation if enabled
        if self.enable_logging:
            self._log_evaluation(
                image=image,
                prompt=prompt,
                result=result,
                raw_response=raw_response,
                character_refs=character_refs,
                story_id=story_id,
                spread_number=spread_number,
                check_text_free=check_text_free,
                check_characters=check_characters,
                check_composition=check_composition,
            )

        return result

    def _log_evaluation(
        self,
        image: Image.Image,
        prompt: str,
        result: "DetailedCheckResult",
        raw_response: str,
        character_refs: Optional[list[tuple[str, Image.Image, str]]],
        story_id: Optional[str],
        spread_number: Optional[int],
        check_text_free: bool,
        check_characters: bool,
        check_composition: bool,
    ) -> None:
        """Log evaluation to database for later annotation."""
        import asyncio
        from backend.api.database.vlm_eval_repository import VLMEvalRepository

        async def _do_log():
            await VLMEvalRepository.log_evaluation(
                image=image,
                prompt=prompt,
                result=result,
                raw_response=raw_response,
                model=self.model,
                character_refs=character_refs,
                story_id=story_id,
                spread_number=spread_number,
                check_text_free=check_text_free,
                check_characters=check_characters,
                check_composition=check_composition,
            )

        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, create a task
            loop.create_task(_do_log())
        except RuntimeError:
            # No running loop, run synchronously
            asyncio.run(_do_log())

    def _build_evaluation_prompt(
        self,
        prompt: str,
        check_text_free: bool,
        check_characters: bool,
        check_composition: bool,
    ) -> str:
        """Build the evaluation prompt for the VLM."""
        sections = [f"""Evaluate this children's book illustration against the following criteria.

ORIGINAL PROMPT:
{prompt}

Respond with valid JSON only. No markdown, no explanation, just the JSON object."""]

        json_fields = []

        if check_text_free:
            json_fields.append('''"text_free": true/false (true if NO text, words, letters, numbers, signs, or writing visible anywhere in the image),
"text_detected": "description of any text found, or 'none'"''')

        if check_characters:
            json_fields.append('''"reference_hair_style": "describe EXACTLY the hair style in REFERENCE (e.g. 'two pigtails with red ties', 'short bob', 'long ponytail')",
"scene_hair_style": "describe EXACTLY the hair style in SCENE",
"hair_matches": true/false (ONLY true if hair style is IDENTICAL - 'pigtails' is NOT the same as 'ponytail' or 'bob'!),
"reference_face_description": "describe face in REFERENCE (round childish vs angular mature, big eyes vs smaller eyes)",
"scene_face_description": "describe face in SCENE",
"face_matches": true/false (true only if face looks the same age/maturity level),
"reference_apparent_age": "estimated age in REFERENCE (e.g. '6-8 years old', '10-12 years old')",
"scene_apparent_age": "estimated age in SCENE",
"age_matches": true/false (true only if apparent ages are within ~2 years - an 8yo should NOT look 12!),
"character_match_score": 1-5 (
  AUTOMATIC score 1-2 if: hair_matches=false OR face_matches=false OR age_matches=false
  Score 3: minor differences only
  Score 4-5: virtually identical appearance),
"character_issues": ["be very specific about differences"]''')

        if check_composition:
            json_fields.append('''"scene_accuracy_score": 1-5 (how well the scene matches the prompt description),
"scene_issues": ["what's", "wrong", "or", "missing"] (empty array if none),
"composition_score": 1-5 (layout quality, space for text overlay, clear focal point),
"style_score": 1-5 (appropriate style for children's picture book)''')

        json_fields.append('''"overall_pass": true/false (true if image is acceptable for the book),
"issues": ["all", "problems", "found"] (empty array if none)''')

        json_template = "{\n  " + ",\n  ".join(json_fields) + "\n}"
        sections.append(f"Return this exact JSON structure:\n{json_template}")

        return "\n\n".join(sections)

    def _parse_response(self, response_text: str) -> DetailedCheckResult:
        """Parse VLM JSON response into DetailedCheckResult."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            text = response_text.strip()
            if text.startswith("```"):
                # Remove markdown code block
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

            start = text.find('{')
            end = text.rfind('}') + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON object found in response")

            data = json.loads(text[start:end])

            # Get base character score
            character_score = int(data.get("character_match_score", 5))
            character_issues = data.get("character_issues", [])

            # Enforce strict matching on key features
            hair_matches = data.get("hair_matches", True)
            face_matches = data.get("face_matches", True)
            age_matches = data.get("age_matches", True)

            if hair_matches is False:
                character_score = min(character_score, 2)
                ref_hair = data.get("reference_hair_style", "")
                scene_hair = data.get("scene_hair_style", "")
                if ref_hair and scene_hair:
                    character_issues.append(f"Hair mismatch: reference has '{ref_hair}', scene has '{scene_hair}'")

            if face_matches is False:
                character_score = min(character_score, 2)
                ref_face = data.get("reference_face_description", "")
                scene_face = data.get("scene_face_description", "")
                if ref_face and scene_face:
                    character_issues.append(f"Face mismatch: reference has '{ref_face}', scene has '{scene_face}'")

            if age_matches is False:
                character_score = min(character_score, 2)
                ref_age = data.get("reference_apparent_age", "")
                scene_age = data.get("scene_apparent_age", "")
                if ref_age and scene_age:
                    character_issues.append(f"Age mismatch: reference looks '{ref_age}', scene looks '{scene_age}'")

            return DetailedCheckResult(
                text_free=data.get("text_free", True),
                text_detected=data.get("text_detected", "none"),
                character_match_score=character_score,
                character_issues=character_issues,
                scene_accuracy_score=int(data.get("scene_accuracy_score", 5)),
                scene_issues=data.get("scene_issues", []),
                composition_score=int(data.get("composition_score", 5)),
                style_score=int(data.get("style_score", 5)),
                overall_pass=data.get("overall_pass", True),
                issues=data.get("issues", []),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # If parsing fails, assume pass but flag the issue
            return DetailedCheckResult(
                text_free=True,
                text_detected="[parse error]",
                character_match_score=3,
                character_issues=[f"VLM response parse error: {e}"],
                scene_accuracy_score=3,
                scene_issues=[],
                composition_score=3,
                style_score=3,
                overall_pass=True,  # Don't block on parse errors
                issues=[f"Warning: Could not parse VLM response: {str(e)[:100]}"],
            )
