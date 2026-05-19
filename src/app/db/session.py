"""Async SQLAlchemy engine, session factory, and dependency provider."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _build_engine() -> AsyncEngine:
    connect_args: dict[str, object] = {}
    if settings.db_statement_timeout_ms > 0:
        # asyncpg respects a per-connection statement_timeout via server_settings.
        connect_args["server_settings"] = {
            "statement_timeout": str(settings.db_statement_timeout_ms),
        }

    return create_async_engine(
        str(settings.database_url),
        echo=settings.db_echo,
        pool_pre_ping=settings.db_pool_pre_ping,
        pool_recycle=settings.db_pool_recycle,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        connect_args=connect_args,
        future=True,
    )


engine: AsyncEngine = _build_engine()

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a transactional ``AsyncSession``.

    Commits on success and rolls back on exception, ensuring the session is
    always closed.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()


async def verify_connectivity() -> None:
    """Run a trivial query at startup so misconfigurations fail fast."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("database_connection_verified")


async def dispose_engine() -> None:
    await engine.dispose()
    logger.info("database_engine_disposed")


__all__ = [
    "AsyncSessionLocal",
    "dispose_engine",
    "engine",
    "get_session",
    "verify_connectivity",
]
