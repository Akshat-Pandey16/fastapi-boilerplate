"""User-facing Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field

UsernameField = Annotated[
    str,
    Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$"),
]
FullNameField = Annotated[str, Field(min_length=1, max_length=150)]


class _UserBase(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        extra="forbid",
    )


class UserCreate(_UserBase):
    username: UsernameField
    email: EmailStr
    full_name: FullNameField | None = None
    is_active: bool = True
    is_superuser: bool = False


class UserUpdate(_UserBase):
    username: UsernameField | None = None
    email: EmailStr | None = None
    full_name: FullNameField | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None


class UserPublic(_UserBase):
    id: uuid.UUID
    username: str
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


__all__ = ["UserCreate", "UserPublic", "UserUpdate"]
