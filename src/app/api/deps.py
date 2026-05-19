"""Shared FastAPI dependencies.

Composing these via ``Annotated[..., Depends(...)]`` keeps endpoint signatures
short and self-documenting.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.user import UserRepository
from app.services.user import UserService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_user_repository(session: SessionDep) -> UserRepository:
    return UserRepository(session)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]


def get_user_service(repository: UserRepositoryDep) -> UserService:
    return UserService(repository)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


__all__ = [
    "SessionDep",
    "UserRepositoryDep",
    "UserServiceDep",
    "get_user_repository",
    "get_user_service",
]
