"""Application settings, loaded from the environment or a local ``.env``.

Settings are validated at import time, so a misconfigured deployment fails
before it serves traffic rather than on the first request.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from contextlib import suppress
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Self

from pydantic import AnyHttpUrl, Field, SecretStr, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine.url import URL

DEFAULT_SECRET_KEY = "change-me-in-production"  # noqa: S105 - a placeholder, rejected in production


class Environment(StrEnum):
    """Deployment environments."""

    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class LogLevel(StrEnum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseBackend(StrEnum):
    """Supported database backends.

    ``sqlite`` needs no server at all, so the project runs on a fresh machine
    with zero infrastructure. The other three are server-backed; pick whichever
    your team already operates.
    """

    POSTGRES = "postgres"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"


#: SQLAlchemy driver per relational backend. MongoDB is absent on purpose —
#: it does not go through SQLAlchemy (see ``app.db.mongo``).
SQL_DRIVERS = {
    DatabaseBackend.POSTGRES: "postgresql+asyncpg",
    DatabaseBackend.MYSQL: "mysql+aiomysql",
    DatabaseBackend.SQLITE: "sqlite+aiosqlite",
}

DEFAULT_PORTS = {
    DatabaseBackend.POSTGRES: 5432,
    DatabaseBackend.MYSQL: 3306,
    DatabaseBackend.MONGODB: 27017,
}


def _backend_from_url(url: str) -> DatabaseBackend | None:
    """Infer the backend from a DSN scheme, or ``None`` if unsupported."""
    scheme = url.split("://", 1)[0].split("+", 1)[0].lower()
    return {
        "postgres": DatabaseBackend.POSTGRES,
        "postgresql": DatabaseBackend.POSTGRES,
        "mysql": DatabaseBackend.MYSQL,
        "mariadb": DatabaseBackend.MYSQL,
        "sqlite": DatabaseBackend.SQLITE,
        "mongodb": DatabaseBackend.MONGODB,
    }.get(scheme)


def _normalise_url(url: str) -> str:
    """Add the async driver to a driverless DSN.

    Hosting platforms inject bare DSNs like ``postgres://…``; SQLAlchemy would
    then pick a blocking driver. Explicit ``+driver`` DSNs are left untouched.
    """
    scheme, separator, remainder = url.partition("://")
    if not separator or "+" in scheme:
        return url
    backend = _backend_from_url(url)
    if backend is None or backend is DatabaseBackend.MONGODB:
        return url
    return f"{SQL_DRIVERS[backend]}://{remainder}"


def _clean(items: Iterable[Any]) -> list[str]:
    return [text for text in (str(item).strip() for item in items) if text]


def _split_csv(value: str | list[str]) -> list[str]:
    """Accept ``a,b`` or ``["a", "b"]`` for sequence-valued env vars."""
    if isinstance(value, list):
        return _clean(value)
    value = value.strip()
    if not value:
        return []
    if value.startswith("["):
        with suppress(json.JSONDecodeError):
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return _clean(parsed)
    return _clean(value.split(","))


class Settings(BaseSettings):
    """Top-level application settings.

    Related options share an env prefix (``DB_``, ``API_``, ``CORS_``) so the
    ``.env`` file stays readable.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application -------------------------------------------------------
    environment: Environment = Field(default=Environment.LOCAL)
    debug: bool = Field(default=False)
    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_json: bool = Field(default=False, description="Emit JSON logs (recommended in production).")

    # --- API ---------------------------------------------------------------
    api_title: str = Field(default="FastAPI Boilerplate")
    api_description: str = Field(
        default="Production-grade FastAPI boilerplate with async SQLAlchemy and Pydantic v2."
    )
    api_version: str = Field(default="0.1.0")
    api_prefix: str = Field(default="/api")
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_reload: bool = Field(default=False)
    api_workers: int = Field(default=1, ge=1)

    # --- CORS --------------------------------------------------------------
    # ``NoDecode`` stops pydantic-settings from JSON-parsing the raw env value
    # so ``_coerce_csv`` below can accept ``CORS_ORIGINS=http://a,http://b``.
    cors_origins: Annotated[list[str], NoDecode, Field(default_factory=list)]
    cors_allow_credentials: bool = True
    cors_allow_methods: Annotated[list[str], NoDecode, Field(default_factory=lambda: ["*"])]
    cors_allow_headers: Annotated[list[str], NoDecode, Field(default_factory=lambda: ["*"])]
    cors_expose_headers: Annotated[
        list[str],
        NoDecode,
        Field(default_factory=lambda: ["X-Request-ID", "X-Response-Time-ms"]),
    ]

    # --- Database ----------------------------------------------------------
    # ``DATABASE_URL`` is the escape hatch: set it and every ``DB_*`` option
    # below is ignored. Managed platforms usually inject exactly this.
    db_url_override: str | None = Field(default=None, validation_alias="DATABASE_URL")

    db_backend: DatabaseBackend = DatabaseBackend.POSTGRES
    db_user: str = "postgres"
    db_password: SecretStr = SecretStr("postgres")
    db_host: str = "localhost"
    db_port: int | None = Field(default=None, ge=1, le=65535, description="Defaults per backend.")
    db_name: str = "fastapi_db"
    db_sqlite_path: Path = Field(default=Path("app.db"), description="Used when DB_BACKEND=sqlite.")

    db_echo: bool = False
    db_pool_size: int = Field(default=10, ge=1)
    db_max_overflow: int = Field(default=20, ge=0)
    db_pool_pre_ping: bool = True
    db_pool_recycle: int = Field(default=1800, ge=0)
    db_statement_timeout_ms: int = Field(default=30_000, ge=0)

    # --- Security ----------------------------------------------------------
    secret_key: SecretStr = SecretStr(DEFAULT_SECRET_KEY)
    request_id_header: str = "X-Request-ID"

    # ----------------------------------------------------------------------
    # Validators
    # ----------------------------------------------------------------------
    @field_validator(
        "cors_origins",
        "cors_allow_methods",
        "cors_allow_headers",
        "cors_expose_headers",
        mode="before",
    )
    @classmethod
    def _coerce_csv(cls, value: str | list[str]) -> list[str]:
        return _split_csv(value)

    @field_validator("db_port", "db_url_override", mode="before")
    @classmethod
    def _blank_means_unset(cls, value: Any) -> Any:
        """Treat ``DB_PORT=`` as "not set" rather than as an invalid value.

        Blank entries are normal in a ``.env`` file and in CI, where an
        undefined variable expands to an empty string.
        """
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("cors_origins")
    @classmethod
    def _validate_origins(cls, value: list[str]) -> list[str]:
        for origin in value:
            if origin == "*":
                continue
            AnyHttpUrl(origin)  # raises for malformed URLs
        return value

    @model_validator(mode="after")
    def _validate_database_url(self) -> Self:
        if self.db_url_override and _backend_from_url(self.db_url_override) is None:
            supported = ", ".join(sorted(b.value for b in DatabaseBackend))
            raise ValueError(
                f"DATABASE_URL scheme {self.db_url_override.split('://', 1)[0]!r} is not "
                f"supported. Supported backends: {supported}."
            )
        return self

    @model_validator(mode="after")
    def _guard_production(self) -> Self:
        """Reject configurations that are unsafe to serve publicly.

        These are mistakes that otherwise surface as a security incident
        rather than as a failed deploy.
        """
        if self.environment is not Environment.PRODUCTION:
            return self

        problems: list[str] = []
        if self.secret_key.get_secret_value() in {DEFAULT_SECRET_KEY, ""}:
            problems.append("SECRET_KEY is still the default — generate a random 32+ byte value")
        if self.debug:
            problems.append("DEBUG must be false in production")
        if "*" in self.cors_origins and self.cors_allow_credentials:
            problems.append(
                "CORS_ORIGINS='*' with CORS_ALLOW_CREDENTIALS=true is rejected by browsers — "
                "list explicit origins"
            )
        if problems:
            raise ValueError("Unsafe production configuration:\n  - " + "\n  - ".join(problems))
        return self

    # ----------------------------------------------------------------------
    # Derived values
    # ----------------------------------------------------------------------
    @property
    def backend(self) -> DatabaseBackend:
        """The backend actually in use, honouring a ``DATABASE_URL`` override."""
        if self.db_url_override:
            return _backend_from_url(self.db_url_override) or self.db_backend
        return self.db_backend

    @property
    def database_url(self) -> str:
        """The DSN the app connects with.

        ``DATABASE_URL`` wins when set; otherwise the DSN is assembled from the
        ``DB_*`` options. ``URL.create`` URL-encodes special characters in
        credentials (``@``, ``/``, ``#``, …) correctly.
        """
        if self.db_url_override:
            return _normalise_url(self.db_url_override)

        if self.backend is DatabaseBackend.SQLITE:
            path = self.db_sqlite_path
            location = str(path) if str(path) == ":memory:" else str(path.expanduser().resolve())
            return f"{SQL_DRIVERS[DatabaseBackend.SQLITE]}:///{location}"

        port = self.db_port or DEFAULT_PORTS[self.backend]
        if self.backend is DatabaseBackend.MONGODB:
            drivername = "mongodb"
            database = None  # Mongo selects the database from the client, not the URI
        else:
            drivername = SQL_DRIVERS[self.backend]
            database = self.db_name

        return URL.create(
            drivername=drivername,
            username=self.db_user or None,
            password=self.db_password.get_secret_value() or None,
            host=self.db_host,
            port=port,
            database=database,
        ).render_as_string(hide_password=False)

    @property
    def is_sql(self) -> bool:
        """True when the backend is relational (SQLAlchemy + Alembic apply)."""
        return self.backend is not DatabaseBackend.MONGODB

    @property
    def is_sqlite(self) -> bool:
        return self.backend is DatabaseBackend.SQLITE

    @property
    def is_mongodb(self) -> bool:
        return self.backend is DatabaseBackend.MONGODB

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.environment is Environment.PRODUCTION

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_test(self) -> bool:
        return self.environment is Environment.TEST

    @computed_field  # type: ignore[prop-decorator]
    @property
    def docs_enabled(self) -> bool:
        """Docs are served everywhere except production."""
        return not self.is_production

    @computed_field  # type: ignore[prop-decorator]
    @property
    def docs_url(self) -> str | None:
        return "/docs" if self.docs_enabled else None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redoc_url(self) -> str | None:
        return "/redoc" if self.docs_enabled else None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def openapi_url(self) -> str | None:
        return f"{self.api_prefix}/openapi.json" if self.docs_enabled else None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor — instantiate exactly once per process."""
    return Settings()


settings = get_settings()
