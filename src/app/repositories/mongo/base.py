"""Generic async CRUD over a MongoDB collection.

Mirrors ``BaseSqlRepository`` so both backends read the same way. Documents
store the domain id under ``_id``; ``_to_document`` hides that translation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pymongo.asynchronous.database import AsyncDatabase


def bson_utcnow() -> datetime:
    """``datetime.now(UTC)`` at the precision BSON can actually store.

    BSON timestamps are milliseconds. Without this truncation a repository
    would return a microsecond-precision value that differs from the one the
    next read gets back — the same document appearing to change on its own.
    """
    now = datetime.now(UTC)
    return now.replace(microsecond=now.microsecond // 1000 * 1000)


class BaseMongoRepository:
    """CRUD primitives shared by concrete Mongo repositories."""

    collection_name: str

    def __init__(self, database: AsyncDatabase[dict[str, Any]]) -> None:
        self.collection = database[self.collection_name]

    @staticmethod
    def _to_document(values: Mapping[str, Any]) -> dict[str, Any]:
        """Move ``id`` to Mongo's ``_id`` primary key."""
        document = dict(values)
        if "id" in document:
            document["_id"] = document.pop("id")
        return document

    @staticmethod
    def _from_document(document: Mapping[str, Any]) -> dict[str, Any]:
        """Move ``_id`` back to ``id``, and BSON's timezone to a plain UTC one.

        The driver returns ``bson.tz_util.FixedOffset``; converting keeps
        timestamps indistinguishable from what the SQL backends return.
        """
        values = dict(document)
        values["id"] = values.pop("_id")
        return {
            key: value.astimezone(UTC) if isinstance(value, datetime) else value
            for key, value in values.items()
        }

    async def fetch_one(self, filter_: Mapping[str, Any]) -> dict[str, Any] | None:
        document = await self.collection.find_one(dict(filter_))
        return None if document is None else self._from_document(document)

    async def fetch_many(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        sort: Sequence[tuple[str, int]] = (),
    ) -> list[dict[str, Any]]:
        cursor = self.collection.find({}).skip(offset).limit(limit)
        if sort:
            cursor = cursor.sort(list(sort))
        return [self._from_document(document) async for document in cursor]

    async def count(self) -> int:
        return await self.collection.count_documents({})

    async def insert(self, values: Mapping[str, Any]) -> dict[str, Any]:
        document = self._to_document(values)
        await self.collection.insert_one(document)
        return self._from_document(document)

    async def update_by_id(self, id_: Any, changes: Mapping[str, Any]) -> Mapping[str, Any] | None:
        document = await self.collection.find_one_and_update(
            {"_id": id_},
            {"$set": dict(changes)},
            return_document=True,
        )
        return None if document is None else self._from_document(document)

    async def commit(self) -> None:
        """No-op: single-document writes are already durable in MongoDB.

        Swap in a client session here if you need multi-document transactions.
        """

    async def delete_by_id(self, id_: Any) -> int:
        result = await self.collection.delete_one({"_id": id_})
        return int(result.deleted_count)


__all__ = ["BaseMongoRepository"]
