"""MongoDB client and request-scoped database handle.

Only imported when ``DB_BACKEND=mongodb``; ``pymongo`` lives behind the
``mongodb`` extra. PyMongo's own ``AsyncMongoClient`` is used here — Motor is
the previous-generation driver and is no longer the recommended path.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any

from bson import UuidRepresentation
from bson.codec_options import CodecOptions
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

#: ``STANDARD`` stores UUIDs as BSON binary subtype 4, which is what every
#: other MongoDB driver expects. ``tz_aware`` makes reads return timezone-aware
#: datetimes, matching what the SQL backends return.
CODEC_OPTIONS: CodecOptions[dict[str, Any]] = CodecOptions(
    uuid_representation=UuidRepresentation.STANDARD,
    tz_aware=True,
)


@lru_cache(maxsize=1)
def get_client() -> AsyncMongoClient[dict[str, Any]]:
    """Return the process-wide Mongo client, creating it on first call."""
    return AsyncMongoClient(
        settings.database_url,
        uuidRepresentation="standard",
        tz_aware=True,
        serverSelectionTimeoutMS=settings.db_statement_timeout_ms or None,
    )


def get_database() -> AsyncDatabase[dict[str, Any]]:
    """Return the configured database handle."""
    return get_client().get_database(settings.db_name, codec_options=CODEC_OPTIONS)


async def get_mongo_database() -> AsyncIterator[AsyncDatabase[dict[str, Any]]]:
    """FastAPI dependency yielding the database handle.

    The driver pools connections internally, so there is nothing to open or
    close per request.
    """
    yield get_database()


async def verify_connectivity() -> None:
    """Ping the server so misconfiguration fails at startup, not per request."""
    await get_client().admin.command("ping")


async def dispose_client() -> None:
    """Close the client, if one was ever created."""
    if get_client.cache_info().currsize:
        await get_client().close()
        logger.info("mongo_client_closed")


__all__ = [
    "dispose_client",
    "get_client",
    "get_database",
    "get_mongo_database",
    "verify_connectivity",
]
