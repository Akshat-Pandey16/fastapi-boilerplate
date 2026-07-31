"""User service — enforces the rules that hold regardless of storage engine."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from app.core.exceptions import ConflictError, NotFoundError
from app.domain.user import UserRecord
from app.repositories.protocols import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repo = repository

    async def get(self, user_id: uuid.UUID) -> UserRecord:
        user = await self._repo.get(user_id)
        if user is None:
            raise NotFoundError(message=f"User {user_id} not found.")
        return user

    async def list(self, *, offset: int, limit: int) -> tuple[Sequence[UserRecord], int]:
        items = await self._repo.list(offset=offset, limit=limit)
        total = await self._repo.count()
        return items, total

    async def create(self, payload: UserCreate) -> UserRecord:
        await self._ensure_unique(username=payload.username, email=payload.email)
        user = await self._repo.create(payload.model_dump())
        await self._repo.commit()
        return user

    async def update(self, user_id: uuid.UUID, payload: UserUpdate) -> UserRecord:
        current = await self.get(user_id)
        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            return current

        # Only re-check a field the caller is actually changing.
        new_username = changes.get("username")
        new_email = changes.get("email")
        await self._ensure_unique(
            username=new_username if new_username != current.username else None,
            email=new_email if new_email != current.email else None,
        )

        updated = await self._repo.update(user_id, changes)
        if updated is None:  # deleted between the read and the write
            raise NotFoundError(message=f"User {user_id} not found.")
        await self._repo.commit()
        return updated

    async def delete(self, user_id: uuid.UUID) -> None:
        if not await self._repo.delete(user_id):
            raise NotFoundError(message=f"User {user_id} not found.")
        await self._repo.commit()

    async def _ensure_unique(self, *, username: str | None, email: str | None) -> None:
        """Fail early with a clear field-level error.

        This is a courtesy check, not the guarantee: two concurrent requests can
        both pass it. The unique index is what actually enforces uniqueness, and
        the resulting integrity error is translated into the same 409.
        """
        if username and await self._repo.get_by_username(username):
            raise ConflictError(message="Username already taken.", details={"field": "username"})
        if email and await self._repo.get_by_email(email):
            raise ConflictError(message="Email already registered.", details={"field": "email"})


__all__ = ["UserService"]
