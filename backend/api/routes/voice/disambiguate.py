"""Homograph disambiguation endpoint using LLM."""

import logging
import re

import dspy
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...dependencies import CurrentUser
from ....config.llm import get_inference_lm
from ....core.homographs import HOMOGRAPHS, get_disambiguation_prompt

logger = logging.getLogger(__name__)

router = APIRouter()


class DisambiguateRequest(BaseModel):
    """Request body for /voice/disambiguate endpoint."""

    word: str = Field(..., min_length=1, max_length=50, description="Word to disambiguate")
    sentence: str = Field(
        ..., min_length=1, max_length=1000, description="Sentence containing the word"
    )
    occurrence: int = Field(
        default=1, ge=1, le=10, description="Which occurrence of the word (1-indexed)"
    )


class DisambiguateResponse(BaseModel):
    """Response body for /voice/disambiguate endpoint."""

    word: str
    pronunciation_index: int = Field(description="0 or 1 indicating which pronunciation")
    phonemes: str | None = Field(description="IPA phonemes for TTS, or None if not a homograph")
    is_homograph: bool


class HomographDisambiguator(dspy.Signature):
    """Determine correct pronunciation of a homograph based on sentence context.

    Given a word with multiple pronunciations and the sentence it appears in,
    determine which pronunciation is correct based on the meaning in context.
    """

    prompt: str = dspy.InputField(desc="The disambiguation prompt with options")
    answer: str = dspy.OutputField(desc="Just 0 or 1 indicating the correct pronunciation")


def parse_llm_response(response_text: str) -> int | None:
    """Parse the LLM response to extract 0 or 1. Returns None if parsing fails."""
    text = response_text.strip()

    # Direct match
    if text == "0":
        return 0
    if text == "1":
        return 1

    # Look for 0 or 1 at the start
    if text.startswith("0"):
        return 0
    if text.startswith("1"):
        return 1

    # Search for standalone 0 or 1
    match = re.search(r"\b([01])\b", text)
    if match:
        return int(match.group(1))

    return None


@router.post("/disambiguate", response_model=DisambiguateResponse)
async def disambiguate_homograph(
    request: DisambiguateRequest,
    current_user: CurrentUser,
) -> DisambiguateResponse:
    """
    Disambiguate a homograph word based on sentence context.

    Uses an LLM to determine the correct pronunciation of a word that has
    multiple valid pronunciations depending on meaning.

    Returns the pronunciation index (0 or 1) and the corresponding IPA phonemes.
    For non-homograph words, returns index 0 with is_homograph=False.
    """
    word = request.word.strip()
    sentence = request.sentence.strip()
    occurrence = request.occurrence
    normalized = word.lower()

    # Check if it's a known homograph
    entry = HOMOGRAPHS.get(normalized)
    if not entry:
        logger.debug(f"Word '{word}' is not a homograph, returning default")
        return DisambiguateResponse(
            word=word,
            pronunciation_index=0,
            phonemes=None,
            is_homograph=False,
        )

    # Build the prompt using the canonical function (no_think=False for DSPy)
    prompt = get_disambiguation_prompt(word, sentence, no_think=False, occurrence=occurrence)
    if not prompt:
        return DisambiguateResponse(
            word=word,
            pronunciation_index=0,
            phonemes=None,
            is_homograph=False,
        )

    logger.info(f"Disambiguating '{word}' in context: {sentence[:50]}...")

    try:
        lm = get_inference_lm()
        predictor = dspy.Predict(HomographDisambiguator)

        with dspy.context(lm=lm):
            result = predictor(prompt=prompt)

        pronunciation_index = parse_llm_response(result.answer)

        if pronunciation_index is None:
            logger.warning(f"Could not parse LLM response: {result.answer}, defaulting to 0")
            pronunciation_index = 0

        phonemes = entry["pronunciations"][pronunciation_index]
        logger.info(f"Disambiguated '{word}' to pronunciation {pronunciation_index}: {phonemes}")

        return DisambiguateResponse(
            word=word,
            pronunciation_index=pronunciation_index,
            phonemes=phonemes,
            is_homograph=True,
        )

    except Exception as e:
        logger.error(f"Disambiguation failed for '{word}': {e}")
        raise HTTPException(status_code=500, detail="Failed to disambiguate word")
