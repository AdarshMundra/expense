from __future__ import annotations

import logging
import re
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database.base import Base

logger = logging.getLogger(__name__)


def _clean_pg_url(url: str) -> tuple[str, dict]:
    """Strip asyncpg-incompatible query params and return (clean_url, connect_args)."""
    connect_args: dict = {}
    needs_ssl = "sslmode=require" in url or "sslmode=prefer" in url
    if needs_ssl:
        connect_args["ssl"] = True
    # Remove params asyncpg rejects
    clean = re.sub(r"[?&]sslmode=[^&]*", "", url)
    clean = re.sub(r"[?&]channel_binding=[^&]*", "", clean)
    # Fix orphaned '?' if all params were stripped
    clean = re.sub(r"\?$", "", clean)
    return clean, connect_args

# Global engine and session factory
_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def _create_engine() -> AsyncEngine:
    """Create the async engine based on DATABASE_URL."""
    database_url = settings.database_url

    if database_url.startswith("sqlite"):
        # SQLite-specific settings for async
        engine = create_async_engine(
            database_url,
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        # PostgreSQL and other databases
        clean_url, connect_args = _clean_pg_url(database_url)
        engine = create_async_engine(
            clean_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            connect_args=connect_args,
        )

    return engine


def get_engine() -> AsyncEngine:
    """Get or create the async engine (singleton)."""
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the session factory (singleton)."""
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False,
        )
    return _async_session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager that provides a database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize the database by creating all tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        # Import all models so they're registered with Base
        from app.database import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully.")


async def close_db() -> None:
    """Close the database engine."""
    global _engine, _async_session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
    logger.info("Database connection closed.")
