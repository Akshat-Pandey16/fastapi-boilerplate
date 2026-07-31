"""Generic async CRUD over SQLAlchemy.

Subclass for domain-specific queries; keeping every ``select()`` behind this
boundary is what keeps the service layer free of SQLAlchemy.

Methods here speak in ORM instances. Concrete repositories translate those to
domain records so nothing above them depends on SQLAlchemy.
"""

from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import CursorResult, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnExpressionArgument

from app.db.base import Base


class BaseSqlRepository[ModelT: Base]:
    """CRUD primitives shared by concrete SQL repositories."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def fetch(self, id_: Any) -> ModelT | None:
        return await self.session.get(self.model, id_)

    async def fetch_one(self, *where: ColumnExpressionArgument[bool]) -> ModelT | None:
        result = await self.session.execute(select(self.model).where(*where))
        return result.scalar_one_or_none()

    async def fetch_many(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        order_by: Sequence[Any] = (),
    ) -> Sequence[ModelT]:
        stmt = select(self.model).offset(offset).limit(limit)
        if order_by:
            stmt = stmt.order_by(*order_by)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(self.model))
        return int(result.scalar_one())

    async def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def remove(self, instance: ModelT) -> None:
        await self.session.delete(instance)
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def remove_by_id(self, id_: Any) -> int:
        stmt = delete(self.model).where(self.model.id == id_)  # type: ignore[attr-defined]
        result = cast(CursorResult[Any], await self.session.execute(stmt))
        await self.session.flush()
        return int(result.rowcount or 0)


__all__ = ["BaseSqlRepository"]
