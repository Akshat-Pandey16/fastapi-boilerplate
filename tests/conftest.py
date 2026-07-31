"""Shared pytest fixtures.

Every test gets its own in-memory SQLite database, so the suite needs no
server, stays hermetic, and never leaks rows between tests.

``ENVIRONMENT=test`` must be set before ``app`` is imported, because settings
are read once at import time.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("DB_SQLITE_PATH", ":memory:")

from app.db.base import Base
from app.db.session import get_session
from app.main import create_app
from app.models import User  # noqa: F401  — registers the model on Base.metadata


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        # StaticPool keeps one connection alive, which is what makes an
        # in-memory database outlive a single checkout.
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """An HTTP client driving the real app, wired to the test database."""
    app = create_app()

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = _override_get_session
    async with (
        LifespanManager(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client
    app.dependency_overrides.clear()
