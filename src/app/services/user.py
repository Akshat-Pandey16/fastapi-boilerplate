"""User service — orchestrates repository calls and enforces invariants."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from app.core.exceptions import ConflictError, NotFoundError
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repo = repository

    async def get(self, user_id: uuid.UUID) -> User:
        user = await self._repo.get(user_id)
        if user is None:
            raise NotFoundError(message=f"User {user_id} not found.")
        return user

    async def list(self, *, offset: int, limit: int) -> tuple[Sequence[User], int]:
        items = await self._repo.list(offset=offset, limit=limit, order_by=User.created_at.desc())
        total = await self._repo.count()
        return items, total

    async def create(self, payload: UserCreate) -> User:
        if await self._repo.get_by_username(payload.username):
            raise ConflictError(
                message="Username already taken.",
                details={"field": "username"},
            )
        if await self._repo.get_by_email(payload.email):
            raise ConflictError(
                message="Email already registered.",
                details={"field": "email"},
            )
        user = User(**payload.model_dump())
        return await self._repo.add(user)

    async def update(self, user_id: uuid.UUID, payload: UserUpdate) -> User:
        user = await self.get(user_id)
        data = payload.model_dump(exclude_unset=True)

        new_username = data.get("username")
        if (
            new_username
            and new_username != user.username
            and await self._repo.get_by_username(new_username)
        ):
            raise ConflictError(
                message="Username already taken.",
                details={"field": "username"},
            )

        new_email = data.get("email")
        if new_email and new_email != user.email and await self._repo.get_by_email(new_email):
            raise ConflictError(
                message="Email already registered.",
                details={"field": "email"},
            )

        for field, value in data.items():
            setattr(user, field, value)
        return await self._repo.add(user)

    async def delete(self, user_id: uuid.UUID) -> None:
        user = await self.get(user_id)
        await self._repo.delete(user)


__all__ = ["UserService"]
