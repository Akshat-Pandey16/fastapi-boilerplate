"""User repository for MongoDB."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pymongo import ASCENDING, DESCENDING, IndexModel

from app.domain.user import UserRecord
from app.repositories.mongo.base import BaseMongoRepository

if TYPE_CHECKING:
    from pymongo.asynchronous.database import AsyncDatabase

COLLECTION = "users"

#: Mongo has no migrations, so uniqueness lives here and is applied at startup
#: by ``ensure_indexes``. This is the counterpart of the SQL unique constraints.
INDEXES = [
    IndexModel([("username", ASCENDING)], name="uq_users_username", unique=True),
    IndexModel([("email", ASCENDING)], name="uq_users_email", unique=True),
    IndexModel([("created_at", DESCENDING), ("_id", DESCENDING)], name="ix_users_created_at"),
]


class MongoUserRepository(BaseMongoRepository):
    """Implements the ``UserRepository`` protocol over MongoDB."""

    collection_name = COLLECTION

    @staticmethod
    def _to_record(document: Mapping[str, Any]) -> UserRecord:
        return UserRecord.model_validate(dict(document))

    async def get(self, user_id: uuid.UUID) -> UserRecord | None:
        document = await self.fetch_one({"_id": user_id})
        return None if document is None else self._to_record(document)

    async def get_by_username(self, username: str) -> UserRecord | None:
        document = await self.fetch_one({"username": username})
        return None if document is None else self._to_record(document)

    async def get_by_email(self, email: str) -> UserRecord | None:
        document = await self.fetch_one({"email": email})
        return None if document is None else self._to_record(document)

    async def list(self, *, offset: int, limit: int) -> Sequence[UserRecord]:
        documents = await self.fetch_many(
            offset=offset,
            limit=limit,
            sort=(("created_at", DESCENDING), ("_id", DESCENDING)),
        )
        return [self._to_record(document) for document in documents]

    async def create(self, values: Mapping[str, Any]) -> UserRecord:
        now = datetime.now(UTC)
        document = await self.insert(
            {"id": uuid.uuid4(), **values, "created_at": now, "updated_at": now}
        )
        return self._to_record(document)

    async def update(self, user_id: uuid.UUID, changes: Mapping[str, Any]) -> UserRecord | None:
        document = await self.update_by_id(user_id, {**changes, "updated_at": datetime.now(UTC)})
        return None if document is None else self._to_record(document)

    async def delete(self, user_id: uuid.UUID) -> bool:
        return await self.delete_by_id(user_id) > 0


async def ensure_indexes(database: AsyncDatabase[dict[str, Any]]) -> None:
    """Create the collection's indexes if they are missing (idempotent)."""
    await database[COLLECTION].create_indexes(INDEXES)


__all__ = ["INDEXES", "MongoUserRepository", "ensure_indexes"]
