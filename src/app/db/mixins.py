"""Reusable model mixins."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    """Adds ``created_at`` and ``updated_at`` columns.

    Values are generated in Python so they are timezone-aware on every backend
    (MySQL and SQLite do not store offsets) and are readable straight after a
    flush without a round trip. The server defaults are a safety net for rows
    inserted by hand or by a migration.
    """

    created_at: Mapped[datetime] = mapped_column(
        default=utcnow,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
        nullable=False,
    )


__all__ = ["TimestampMixin", "utcnow"]
