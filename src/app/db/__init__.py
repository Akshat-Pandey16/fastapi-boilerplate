"""Database layer.

Exposes one connectivity check and one shutdown hook that work for whichever
backend is configured, so callers (lifespan, health probes) never branch on it.
Backend modules are imported lazily because ``pymongo`` is an optional extra.
"""

from app.core.config import settings
from app.db.base import Base
from app.db.mixins import TimestampMixin


async def ping() -> None:
    """Verify the configured database answers. Raises on failure."""
    if settings.is_sql:
        from app.db.session import verify_connectivity  # noqa: PLC0415
    else:
        from app.db.mongo import verify_connectivity  # noqa: PLC0415
    await verify_connectivity()


async def shutdown() -> None:
    """Release pooled connections held by the configured backend."""
    if settings.is_sql:
        from app.db.session import dispose_engine  # noqa: PLC0415

        await dispose_engine()
    else:
        from app.db.mongo import dispose_client  # noqa: PLC0415

        await dispose_client()


__all__ = ["Base", "TimestampMixin", "ping", "shutdown"]
