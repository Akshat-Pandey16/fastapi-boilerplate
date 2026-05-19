"""Declarative SQLAlchemy base with sensible defaults."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

_CAMEL_TO_SNAKE = re.compile(r"(?<!^)(?=[A-Z])")


class Base(DeclarativeBase):
    """Project-wide SQLAlchemy declarative base.

    - Uses a consistent metadata naming convention so Alembic produces
      deterministic constraint names across environments.
    - Auto-derives ``__tablename__`` from the class name (CamelCase → snake_case)
      unless the subclass sets one explicitly.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {
        datetime: __import__("sqlalchemy").types.DateTime(timezone=True),
    }

    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        return _CAMEL_TO_SNAKE.sub("_", cls.__name__).lower()

    def __repr__(self) -> str:
        attrs = ", ".join(
            f"{column.name}={getattr(self, column.name)!r}" for column in self.__table__.primary_key
        )
        return f"<{type(self).__name__}({attrs})>"

    def to_dict(self) -> dict[str, Any]:
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


__all__ = ["Base"]
