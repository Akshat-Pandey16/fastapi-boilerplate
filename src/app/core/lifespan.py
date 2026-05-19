"""Application lifespan — startup/shutdown hooks."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import dispose_engine, verify_connectivity

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run startup checks, then dispose resources on shutdown."""
    logger.info(
        "startup",
        service=settings.api_title,
        version=settings.api_version,
        environment=settings.environment,
    )

    if not settings.is_test:
        await verify_connectivity()

    yield

    logger.info("shutdown", service=settings.api_title)
    await dispose_engine()


__all__ = ["lifespan"]
