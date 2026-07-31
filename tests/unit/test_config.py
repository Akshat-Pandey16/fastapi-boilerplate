"""Unit tests for settings resolution."""

from __future__ import annotations

import os
from collections.abc import Callable

import pytest
from pydantic import ValidationError

from app.core.config import DatabaseBackend, Settings

Builder = Callable[..., Settings]

_PREFIXES = ("DB_", "API_", "CORS_", "LOG_")
_NAMES = ("ENVIRONMENT", "DEBUG", "SECRET_KEY", "DATABASE_URL", "REQUEST_ID_HEADER")


@pytest.fixture
def build(monkeypatch: pytest.MonkeyPatch) -> Builder:
    """Build Settings from an exact environment, ignoring the developer's .env.

    Settings are read from the environment, so the environment is what a test
    has to control — passing keyword arguments would bypass the code under test.
    """

    def _build(**env: str) -> Settings:
        for key in list(os.environ):
            if key.startswith(_PREFIXES) or key in _NAMES:
                monkeypatch.delenv(key, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        return Settings(_env_file=None)

    return _build


@pytest.mark.unit
def test_defaults_to_postgres_dsn(build: Builder) -> None:
    settings = build()
    assert settings.backend is DatabaseBackend.POSTGRES
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert ":5432/" in settings.database_url  # port falls back per backend


@pytest.mark.unit
@pytest.mark.parametrize(
    ("backend", "expected_port"),
    [("postgres", 5432), ("mysql", 3306), ("mongodb", 27017)],
)
def test_port_defaults_per_backend(build: Builder, backend: str, expected_port: int) -> None:
    assert f":{expected_port}" in build(DB_BACKEND=backend).database_url


@pytest.mark.unit
@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_env_values_mean_unset(build: Builder, blank: str) -> None:
    """`DB_PORT=` in a .env file must not be a startup failure."""
    settings = build(DB_BACKEND="postgres", DB_PORT=blank, DATABASE_URL=blank)
    assert settings.db_port is None
    assert ":5432/" in settings.database_url


@pytest.mark.unit
def test_sqlite_needs_no_server(build: Builder) -> None:
    settings = build(DB_BACKEND="sqlite", DB_SQLITE_PATH=":memory:")
    assert settings.is_sqlite
    assert settings.is_sql
    assert settings.database_url == "sqlite+aiosqlite:///:memory:"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("url", "expected"),
    [
        # Platforms inject driverless DSNs; SQLAlchemy would pick a blocking driver.
        ("postgres://u:p@h:5432/db", "postgresql+asyncpg://u:p@h:5432/db"),
        ("postgresql://u:p@h:5432/db", "postgresql+asyncpg://u:p@h:5432/db"),
        ("mysql://u:p@h:3306/db", "mysql+aiomysql://u:p@h:3306/db"),
        # An explicit driver is left alone.
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("mongodb://h:27017", "mongodb://h:27017"),
    ],
)
def test_database_url_override_gets_an_async_driver(
    build: Builder, url: str, expected: str
) -> None:
    assert build(DATABASE_URL=url).database_url == expected


@pytest.mark.unit
def test_database_url_override_selects_the_backend(build: Builder) -> None:
    settings = build(DB_BACKEND="postgres", DATABASE_URL="mongodb://localhost:27017")
    assert settings.backend is DatabaseBackend.MONGODB
    assert settings.is_mongodb
    assert not settings.is_sql


@pytest.mark.unit
def test_unsupported_database_url_is_rejected(build: Builder) -> None:
    with pytest.raises(ValidationError, match="not supported"):
        build(DATABASE_URL="cassandra://localhost:9042/db")


@pytest.mark.unit
def test_csv_and_json_cors_origins_both_parse(build: Builder) -> None:
    csv = build(CORS_ORIGINS="http://a.test,http://b.test")
    json_list = build(CORS_ORIGINS='["http://a.test", "http://b.test"]')
    assert csv.cors_origins == json_list.cors_origins == ["http://a.test", "http://b.test"]


@pytest.mark.unit
def test_docs_are_hidden_only_in_production(build: Builder) -> None:
    assert build(ENVIRONMENT="staging").docs_url == "/docs"
    assert build(ENVIRONMENT="production", SECRET_KEY="x" * 40).docs_url is None


@pytest.mark.unit
@pytest.mark.parametrize(
    "env",
    [
        {"ENVIRONMENT": "production"},  # default SECRET_KEY
        {"ENVIRONMENT": "production", "SECRET_KEY": "x" * 40, "DEBUG": "true"},
        {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "x" * 40,
            "CORS_ORIGINS": "*",
            "CORS_ALLOW_CREDENTIALS": "true",
        },
    ],
)
def test_unsafe_production_config_fails_fast(build: Builder, env: dict[str, str]) -> None:
    with pytest.raises(ValidationError, match="Unsafe production configuration"):
        build(**env)


@pytest.mark.unit
def test_safe_production_config_is_accepted(build: Builder) -> None:
    settings = build(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 40,
        CORS_ORIGINS="https://app.example.com",
    )
    assert settings.is_production
