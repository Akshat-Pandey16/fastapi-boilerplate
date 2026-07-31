"""One set of assertions, run against every storage backend.

If a repository stops behaving like the others, this fails — which is the whole
point of ``app.repositories.protocols``. The MongoDB parameter skips itself
when no server is reachable, so the suite still passes on a laptop with
nothing installed.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.protocols import UserRepository
from app.repositories.sql.user import SqlUserRepository

MONGO_URL = "mongodb://localhost:27017"


async def _mongo_repository() -> AsyncIterator[UserRepository]:
    pymongo = pytest.importorskip("pymongo", reason="the mongodb extra is not installed")

    from app.repositories.mongo.user import MongoUserRepository, ensure_indexes  # noqa: PLC0415

    client = pymongo.AsyncMongoClient(
        MONGO_URL,
        uuidRepresentation="standard",
        tz_aware=True,
        serverSelectionTimeoutMS=500,
    )
    try:
        await client.admin.command("ping")
    except Exception as exc:  # no server on this machine — that is fine
        await client.close()
        pytest.skip(f"no MongoDB at {MONGO_URL}: {type(exc).__name__}")

    name = f"boilerplate_test_{uuid.uuid4().hex}"
    database = client.get_database(name)
    await ensure_indexes(database)
    try:
        yield MongoUserRepository(database)
    finally:
        await client.drop_database(name)
        await client.close()


@pytest.fixture(params=["sql", "mongodb"])
async def repository(
    request: pytest.FixtureRequest, session: AsyncSession
) -> AsyncIterator[UserRepository]:
    if request.param == "sql":
        yield SqlUserRepository(session)
        return
    async for repo in _mongo_repository():
        yield repo


def _payload(**overrides: object) -> dict[str, object]:
    return {
        "username": "alice",
        "email": "alice@example.com",
        "full_name": "Alice Example",
        "is_active": True,
        "is_superuser": False,
    } | overrides


@pytest.mark.integration
async def test_create_then_read_back(repository: UserRepository) -> None:
    created = await repository.create(_payload())
    await repository.commit()

    assert created.username == "alice"
    assert created.created_at.tzinfo is not None, "timestamps must be timezone-aware"

    assert (await repository.get(created.id)) == created
    assert (await repository.get_by_username("alice")) == created
    assert (await repository.get_by_email("alice@example.com")) == created


@pytest.mark.integration
async def test_missing_rows_return_none(repository: UserRepository) -> None:
    assert await repository.get(uuid.uuid4()) is None
    assert await repository.get_by_username("nobody") is None
    assert await repository.get_by_email("nobody@example.com") is None


@pytest.mark.integration
async def test_update_changes_only_what_was_passed(repository: UserRepository) -> None:
    created = await repository.create(_payload())
    await repository.commit()

    updated = await repository.update(created.id, {"full_name": "Alice Updated"})
    await repository.commit()

    assert updated is not None
    assert updated.full_name == "Alice Updated"
    assert updated.username == created.username
    assert updated.id == created.id


@pytest.mark.integration
async def test_update_of_a_missing_row_returns_none(repository: UserRepository) -> None:
    assert await repository.update(uuid.uuid4(), {"full_name": "ghost"}) is None


@pytest.mark.integration
async def test_delete_reports_whether_a_row_went(repository: UserRepository) -> None:
    created = await repository.create(_payload())
    await repository.commit()

    assert await repository.delete(created.id) is True
    await repository.commit()
    assert await repository.delete(created.id) is False
    assert await repository.get(created.id) is None


@pytest.mark.integration
async def test_list_is_paginated_and_counted(repository: UserRepository) -> None:
    for idx in range(5):
        await repository.create(_payload(username=f"user{idx}", email=f"user{idx}@example.com"))
    await repository.commit()

    assert await repository.count() == 5

    first = await repository.list(offset=0, limit=2)
    second = await repository.list(offset=2, limit=2)
    assert len(first) == len(second) == 2
    assert {user.id for user in first}.isdisjoint({user.id for user in second})
