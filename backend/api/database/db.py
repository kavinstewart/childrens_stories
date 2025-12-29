"""PostgreSQL database connection management using SQLAlchemy async."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from ..config import DATABASE_URL


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""

    pass


# Create async engine (only if DATABASE_URL is configured)
# Pool settings optimized for story generation workload
engine: Optional[AsyncEngine] = None
async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None

if DATABASE_URL:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # Set to True for SQL debugging
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # Verify connections before use
    )

    # Session factory
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


def _check_configured():
    """Raise an error if the database is not configured."""
    if engine is None or async_session_factory is None:
        raise RuntimeError(
            "Database not configured. Set DATABASE_URL environment variable "
            "to a PostgreSQL connection string."
        )


async def init_db() -> None:
    """Initialize database - create all tables."""
    _check_configured()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database sessions."""
    _check_configured()
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection helper for FastAPI."""
    _check_configured()
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
