"""Transcript summarization endpoint using DSPy."""

import logging

import dspy
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...dependencies import CurrentUser
from ....config.llm import get_inference_lm

logger = logging.getLogger(__name__)

router = APIRouter()


class SummarizeRequest(BaseModel):
    """Request body for /voice/summarize endpoint."""
    transcript: str


class SummarizeResponse(BaseModel):
    """Response body for /voice/summarize endpoint."""
    goal: str
    summary: str


class TranscriptSummarizer(dspy.Signature):
    """Extract a clear story goal from a voice transcript.

    The user has spoken a story idea aloud, possibly with filler words, repetition,
    or rambling. Extract the core story concept and create a clear, concise goal
    that can be used to generate a children's picture book.
    """

    transcript: str = dspy.InputField(
        desc="Raw voice transcript, may contain filler words, repetition, or unclear speech"
    )
    goal: str = dspy.OutputField(
        desc="A clear, concise story goal (1-2 sentences) suitable for generating a children's picture book. Should capture the main theme, characters, and lesson if any."
    )
    summary: str = dspy.OutputField(
        desc="A friendly, conversational summary to read back to the user confirming what story will be created. Start with 'I'll create' or similar."
    )


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_transcript(
    request: SummarizeRequest,
    current_user: CurrentUser,
) -> SummarizeResponse:
    """
    Summarize a voice transcript into a clear story goal.

    Uses an LLM to extract the core story idea from potentially rambling
    or unclear speech, returning both a clean goal for story generation
    and a friendly summary for TTS confirmation.
    """
    transcript = request.transcript.strip()

    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript cannot be empty")

    logger.info(f"Summarizing transcript: {transcript[:100]}...")

    try:
        # Use DSPy to extract goal and summary
        lm = get_inference_lm()
        summarizer = dspy.Predict(TranscriptSummarizer)

        with dspy.context(lm=lm):
            result = summarizer(transcript=transcript)

        logger.info(f"Extracted goal: {result.goal}")

        return SummarizeResponse(
            goal=result.goal,
            summary=result.summary,
        )

    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to summarize transcript")
