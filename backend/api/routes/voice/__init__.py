"""Voice routes for streaming STT via Deepgram and TTS via Cartesia."""

from fastapi import APIRouter

from .stt import router as stt_router
from .tts import router as tts_router
from .summarize import router as summarize_router
from .disambiguate import router as disambiguate_router

router = APIRouter(tags=["Voice"])

# Include all sub-routers
router.include_router(stt_router)
router.include_router(tts_router)
router.include_router(summarize_router)
router.include_router(disambiguate_router)

__all__ = ["router"]
