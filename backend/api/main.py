"""FastAPI application for the Children's Story Generator."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth.routes import router as auth_router
from .config import DATABASE_URL
from .routes import stories, admin
from .services.job_manager import job_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup: Initialize database (only if DATABASE_URL is configured)
    if DATABASE_URL:
        from .database.db import init_db

        await init_db()
        logger.info("Database initialized")
    else:
        logger.warning("DATABASE_URL not set - database not initialized")

    yield

    # Shutdown: Clean up job manager
    job_manager.shutdown(wait=True)


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
app.include_router(admin.router, prefix="/admin", tags=["Admin"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
