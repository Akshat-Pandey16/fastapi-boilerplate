"""Application settings powered by pydantic-settings.

All configuration is loaded from environment variables (or a local ``.env``
file). Settings are validated at startup, so misconfiguration fails loudly
before serving traffic.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, Field, SecretStr, computed_field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine.url import URL


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


def _split_csv(value: str | list[str]) -> list[str] | str:
    """Allow CSV strings or JSON lists for sequence-valued env vars."""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    value = value.strip()
    if not value:
        return []
    if value.startswith("["):  # JSON list — let pydantic parse it
        return value
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    """Top-level application settings.

    Nested sections are grouped via env prefixes (``DB_``, ``API_``, ``CORS_``)
    so that the .env file stays readable.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
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
    api_host: str = Field(default="0.0.0.0")  # noqa: S104 - intentional for containers
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_reload: bool = Field(default=False)
    api_workers: int = Field(default=1, ge=1)

    # --- CORS --------------------------------------------------------------
    # ``NoDecode`` stops pydantic-settings from JSON-parsing the env value so
    # the ``_coerce_csv`` validator below can accept simple comma-separated
    # lists like ``CORS_ORIGINS=http://a,http://b``.
    cors_origins: Annotated[list[str], NoDecode, Field(default_factory=list)]
    cors_allow_credentials: bool = True
    cors_allow_methods: Annotated[list[str], NoDecode, Field(default_factory=lambda: ["*"])]
    cors_allow_headers: Annotated[list[str], NoDecode, Field(default_factory=lambda: ["*"])]

    # --- Database ----------------------------------------------------------
    db_user: str = "postgres"
    db_password: SecretStr = SecretStr("postgres")
    db_host: str = "localhost"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = "fastapi_db"
    db_scheme: Literal["postgresql+asyncpg"] = "postgresql+asyncpg"

    db_echo: bool = False
    db_pool_size: int = Field(default=10, ge=1)
    db_max_overflow: int = Field(default=20, ge=0)
    db_pool_pre_ping: bool = True
    db_pool_recycle: int = Field(default=1800, ge=0)
    db_statement_timeout_ms: int = Field(default=30_000, ge=0)

    # --- Security ----------------------------------------------------------
    secret_key: SecretStr = SecretStr("change-me-in-production")
    request_id_header: str = "X-Request-ID"

    # ----------------------------------------------------------------------
    # Validators
    # ----------------------------------------------------------------------
    @field_validator("cors_origins", "cors_allow_methods", "cors_allow_headers", mode="before")
    @classmethod
    def _coerce_csv(cls, value: str | list[str]) -> list[str] | str:
        return _split_csv(value)

    @field_validator("cors_origins")
    @classmethod
    def _validate_origins(cls, value: list[str]) -> list[str]:
        for origin in value:
            if origin == "*":
                continue
            # Best-effort validation; raises ValidationError for malformed URLs.
            AnyHttpUrl(origin)
        return value

    # ----------------------------------------------------------------------
    # Computed
    # ----------------------------------------------------------------------
    @property
    def database_url(self) -> str:
        """Async SQLAlchemy DSN.

        Built via SQLAlchemy's ``URL.create`` so special characters in the
        username/password (``@``, ``/``, ``#``, …) are URL-encoded correctly.
        """
        return URL.create(
            drivername=self.db_scheme,
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        ).render_as_string(hide_password=False)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.environment is Environment.PRODUCTION

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_development(self) -> bool:
        return self.environment in {Environment.LOCAL, Environment.DEVELOPMENT}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_test(self) -> bool:
        return self.environment is Environment.TEST

    @computed_field  # type: ignore[prop-decorator]
    @property
    def docs_url(self) -> str | None:
        return None if self.is_production else "/docs"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redoc_url(self) -> str | None:
        return None if self.is_production else "/redoc"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def openapi_url(self) -> str | None:
        return None if self.is_production else f"{self.api_prefix}/openapi.json"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor — instantiate exactly once per process."""
    return Settings()


settings = get_settings()
