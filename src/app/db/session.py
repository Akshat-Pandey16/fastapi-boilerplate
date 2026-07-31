"""Async SQLAlchemy engine, session factory, and request-scoped session.

The engine is built on first use rather than at import time, so importing the
app never opens a connection — which keeps the MongoDB backend, test overrides,
and pre-fork servers well behaved.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import DatabaseBackend, settings
from app.core.logging import get_logger

logger = get_logger(__name__)

#: Applied to every new SQLite connection. SQLite ships with foreign keys off
#: and a lock-heavy journal, neither of which suits a web app.
SQLITE_PRAGMAS = (
    "PRAGMA foreign_keys=ON",
    "PRAGMA journal_mode=WAL",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA busy_timeout=5000",
)


def _engine_options() -> dict[str, Any]:
    """Engine keyword arguments that make sense for the configured backend."""
    options: dict[str, Any] = {"echo": settings.db_echo}

    if settings.is_sqlite:
        # A file-backed SQLite database is a local file, not a connection pool;
        # sizing knobs would be rejected by its default pool class.
        return options

    options |= {
        "pool_pre_ping": settings.db_pool_pre_ping,
        "pool_recycle": settings.db_pool_recycle,
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
    }

    if settings.backend is DatabaseBackend.POSTGRES and settings.db_statement_timeout_ms > 0:
        # asyncpg applies these as per-connection server settings.
        options["connect_args"] = {
            "server_settings": {"statement_timeout": str(settings.db_statement_timeout_ms)}
        }

    return options


def _register_sqlite_pragmas(engine: AsyncEngine) -> None:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragmas(dbapi_connection: Any, _: Any) -> None:
        cursor = dbapi_connection.cursor()
        try:
            for pragma in SQLITE_PRAGMAS:
                cursor.execute(pragma)
        finally:
            cursor.close()


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, creating it on first call."""
    if not settings.is_sql:
        raise RuntimeError(
            f"DB_BACKEND={settings.backend.value} does not use SQLAlchemy. "
            "Use app.db.mongo.get_database() instead."
        )
    engine = create_async_engine(settings.database_url, **_engine_options())
    if settings.is_sqlite:
        _register_sqlite_pragmas(engine)
    return engine


@lru_cache(maxsize=1)
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped ``AsyncSession``.

    Committing is the service layer's job — a commit that fails must surface
    while the request is still in flight, not during teardown after the
    response has been sent. This rolls back anything left uncommitted.
    """
    async with get_sessionmaker()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def verify_connectivity() -> None:
    """Run a trivial query so misconfiguration fails at startup, not per request."""
    async with get_engine().connect() as connection:
        await connection.execute(text("SELECT 1"))


async def dispose_engine() -> None:
    """Close pooled connections, if an engine was ever created."""
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
        logger.info("database_engine_disposed")


__all__ = [
    "dispose_engine",
    "get_engine",
    "get_session",
    "get_sessionmaker",
    "verify_connectivity",
]
