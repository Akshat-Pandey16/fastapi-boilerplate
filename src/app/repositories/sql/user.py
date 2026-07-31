"""User repository for the relational backends."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from app.domain.user import UserRecord
from app.models.user import User
from app.repositories.sql.base import BaseSqlRepository


class SqlUserRepository(BaseSqlRepository[User]):
    """Implements the ``UserRepository`` protocol over SQLAlchemy."""

    model = User

    @staticmethod
    def _to_record(user: User) -> UserRecord:
        return UserRecord.model_validate(user)

    async def get(self, user_id: uuid.UUID) -> UserRecord | None:
        user = await self.fetch(user_id)
        return None if user is None else self._to_record(user)

    async def get_by_username(self, username: str) -> UserRecord | None:
        user = await self.fetch_one(User.username == username)
        return None if user is None else self._to_record(user)

    async def get_by_email(self, email: str) -> UserRecord | None:
        user = await self.fetch_one(User.email == email)
        return None if user is None else self._to_record(user)

    async def list(self, *, offset: int, limit: int) -> Sequence[UserRecord]:
        # ``id`` breaks ties so pages stay stable when rows share a timestamp.
        rows = await self.fetch_many(
            offset=offset,
            limit=limit,
            order_by=(User.created_at.desc(), User.id.desc()),
        )
        return [self._to_record(row) for row in rows]

    async def create(self, values: Mapping[str, Any]) -> UserRecord:
        user = await self.add(User(**values))
        return self._to_record(user)

    async def update(self, user_id: uuid.UUID, changes: Mapping[str, Any]) -> UserRecord | None:
        user = await self.fetch(user_id)
        if user is None:
            return None
        for field, value in changes.items():
            setattr(user, field, value)
        await self.session.flush()
        return self._to_record(user)

    async def delete(self, user_id: uuid.UUID) -> bool:
        return await self.remove_by_id(user_id) > 0


__all__ = ["SqlUserRepository"]
