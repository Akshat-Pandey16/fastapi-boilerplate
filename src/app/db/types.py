"""Column types that behave the same on every supported backend."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Dialect, TypeDecorator


class UtcDateTime(TypeDecorator[datetime]):
    """A timestamp that is always timezone-aware UTC in Python.

    PostgreSQL stores the offset; MySQL and SQLite do not, so a value written
    as aware would come back naive and blow up the next time it met an aware
    ``datetime``. This normalises both directions, so application code can
    assume UTC everywhere.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError(
                "Naive datetime rejected: attach a timezone, e.g. datetime.now(UTC). "
                "Storing local time without an offset is not recoverable later."
            )
        return value.astimezone(UTC)

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        stored: datetime = value
        # Backends without offset support hand back a naive value that is UTC.
        return stored.replace(tzinfo=UTC) if stored.tzinfo is None else stored.astimezone(UTC)


__all__ = ["UtcDateTime"]
