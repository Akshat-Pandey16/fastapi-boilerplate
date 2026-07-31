"""Alembic environment configured for async SQLAlchemy and src/ layout."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig
from pathlib import Path
from sys import path as sys_path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Ensure ``src`` is importable regardless of how alembic is invoked.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC = _PROJECT_ROOT / "src"
if str(_SRC) not in sys_path:
    sys_path.insert(0, str(_SRC))

from app.core.config import settings  # noqa: E402
from app.models import Base  # noqa: E402  — registers all models on Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

if not settings.is_sql:
    raise SystemExit(
        f"DB_BACKEND={settings.backend.value} has no schema to migrate. "
        "MongoDB indexes are created at application startup instead."
    )


def _get_url() -> str:
    return settings.database_url


#: SQLite cannot ALTER most things in place; batch mode rewrites the table
#: instead. Harmless on the other backends, but only needed here.
_RENDER_AS_BATCH = settings.is_sqlite


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emit SQL without a live connection."""
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=_RENDER_AS_BATCH,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=_RENDER_AS_BATCH,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_url()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
