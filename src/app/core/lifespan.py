"""Application lifespan — startup checks and shutdown cleanup."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Verify the database is reachable, then release it again on shutdown."""
    logger.info(
        "startup",
        service=settings.api_title,
        version=settings.api_version,
        environment=settings.environment,
        backend=settings.backend,
    )

    if not settings.is_test:
        await db.ping()
        if settings.is_mongodb:
            # MongoDB has no migrations, so uniqueness is applied here.
            from app.db.mongo import get_database  # noqa: PLC0415
            from app.repositories.mongo.user import ensure_indexes  # noqa: PLC0415

            await ensure_indexes(get_database())

    yield

    logger.info("shutdown", service=settings.api_title)
    await db.shutdown()


__all__ = ["lifespan"]
