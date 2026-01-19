"""FastAPI application for the Children's Story Generator."""

import logging
import warnings
from contextlib import asynccontextmanager

# Suppress pydub's ffmpeg warning. pydub is a required dependency of the cartesia
# TTS library, but we only use Cartesia's WebSocket streaming with raw PCM output.
# We never use pydub's audio conversion/concatenation features that require ffmpeg.
warnings.filterwarnings("ignore", message="Couldn't find ffmpeg or avconv")

from arq import create_pool
from arq.connections import RedisSettings
from dotenv import load_dotenv
load_dotenv()  # Must run before importing config

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth.routes import router as auth_router
from .config import DATABASE_URL
from .routes import logs, stories, voice
from . import arq_pool as arq_pool_module

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup: Initialize database (only if DATABASE_URL is configured)
    if DATABASE_URL:
        from .database.db import init_pool, init_db, close_pool

        await init_pool()
        logger.info("Database pool initialized")
        await init_db()
        logger.info("Database schema initialized")
    else:
        logger.warning("DATABASE_URL not set - database not initialized")

    # Startup: Initialize ARQ Redis pool
    try:
        pool = await create_pool(RedisSettings())
        arq_pool_module.set_pool(pool)
        logger.info("ARQ Redis pool initialized")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        logger.warning("Story generation will not work without Redis")

    yield

    # Shutdown: Close database pool
    if DATABASE_URL:
        from .database.db import close_pool
        await close_pool()
        logger.info("Database pool closed")

    # Shutdown: Close ARQ pool
    await arq_pool_module.close_pool()
    logger.info("ARQ Redis pool closed")


app = FastAPI(
    title="Children's Story Generator API",
    description="""
Generate high-quality children's picture books from learning goals or themes.

## Features
- **Text Generation**: Create 15-page stories optimized for 4-7 year olds
- **Quality Iteration**: Stories are judged and regenerated until quality threshold is met
- **Illustrations**: Optionally generate character reference sheets and page illustrations

## Workflow
1. POST `/stories` with your goal to start generation
2. Poll GET `/stories/{id}` until status is `completed` or `failed`
3. Access pages and images via the nested endpoints
    """,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)  # No prefix - already has /auth
app.include_router(stories.router, prefix="/stories", tags=["Stories"])
app.include_router(logs.router, prefix="/logs", tags=["Logs"])
app.include_router(voice.router, prefix="/voice", tags=["Voice"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
