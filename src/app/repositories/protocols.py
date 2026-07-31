"""Repository interfaces.

The service layer depends on these protocols, never on a concrete class, so
swapping PostgreSQL for MongoDB is a wiring change in ``app.api.deps`` rather
than a rewrite of the business logic.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from app.domain.user import UserRecord


class UserRepository(Protocol):
    """Persistence operations the user service needs."""

    async def get(self, user_id: uuid.UUID) -> UserRecord | None: ...

    async def get_by_username(self, username: str) -> UserRecord | None: ...

    async def get_by_email(self, email: str) -> UserRecord | None: ...

    async def list(self, *, offset: int, limit: int) -> Sequence[UserRecord]: ...

    async def count(self) -> int: ...

    async def create(self, values: Mapping[str, Any]) -> UserRecord: ...

    async def update(self, user_id: uuid.UUID, changes: Mapping[str, Any]) -> UserRecord | None: ...

    async def delete(self, user_id: uuid.UUID) -> bool: ...

    async def commit(self) -> None:
        """Make the pending writes of this request durable.

        Services call this once, at the end of a use case, so a failing commit
        is raised while the request is still in flight and can be turned into
        an error response.
        """
        ...


__all__ = ["UserRepository"]
