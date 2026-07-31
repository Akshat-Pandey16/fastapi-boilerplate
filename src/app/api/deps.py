"""Shared FastAPI dependencies.

The repository implementation is chosen once, at import time, from
``DB_BACKEND``. Endpoints and services only ever see the protocol, so adding a
backend means adding an adapter here — not touching the API layer.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.repositories.protocols import UserRepository
from app.services.user import UserService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_sql_user_repository(session: SessionDep) -> UserRepository:
    from app.repositories.sql.user import SqlUserRepository  # noqa: PLC0415

    return SqlUserRepository(session)


async def get_mongo_user_repository() -> UserRepository:
    from app.db.mongo import get_database  # noqa: PLC0415
    from app.repositories.mongo.user import MongoUserRepository  # noqa: PLC0415

    return MongoUserRepository(get_database())


def _user_repository_dependency() -> Any:
    """Bind the repository dependency that matches the configured backend."""
    if settings.is_sql:
        return Depends(get_sql_user_repository)
    return Depends(get_mongo_user_repository)


UserRepositoryDep = Annotated[UserRepository, _user_repository_dependency()]


def get_user_service(repository: UserRepositoryDep) -> UserService:
    return UserService(repository)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


__all__ = [
    "SessionDep",
    "UserRepositoryDep",
    "UserServiceDep",
    "get_mongo_user_repository",
    "get_sql_user_repository",
    "get_user_service",
]
