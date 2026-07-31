"""Storage-independent representation of a user."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserRecord(BaseModel):
    """A user as the service layer sees it.

    Repositories build this from whatever their backend returns — a SQLAlchemy
    row or a BSON document — so nothing above the repository needs to know
    which database is in use.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: str
    full_name: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


__all__ = ["UserRecord"]
