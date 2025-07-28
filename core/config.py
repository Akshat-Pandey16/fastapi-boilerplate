import os
from typing import List
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv(override=True)


class DatabaseConfig:
    USER: str = os.getenv("DB_USER", "postgres")
    PASSWORD: str = os.getenv("DB_PASSWORD", "password")
    DB: str = os.getenv("DB_NAME", "fastapi_db")
    HOST: str = os.getenv("DB_HOST", "localhost")
    PORT: str = os.getenv("DB_PORT", "5432")

    ECHO: bool = os.getenv("DB_ECHO", "true").lower() == "true"
    POOL_PRE_PING: bool = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"
    POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "300"))

    @property
    def URL(self) -> str:
        encoded_password = quote_plus(self.PASSWORD)
        return f"postgresql+asyncpg://{self.USER}:{encoded_password}@{self.HOST}:{self.PORT}/{self.DB}"


class APIConfig:
    TITLE: str = os.getenv("API_TITLE", "FastAPI Boilerplate")
    DESCRIPTION: str = os.getenv(
        "API_DESCRIPTION",
        "A production-ready FastAPI boilerplate with async PostgreSQL",
    )
    VERSION: str = os.getenv("API_VERSION", "1.0.0")
    HOST: str = os.getenv("API_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("API_PORT", "8000"))
    RELOAD: bool = (
        os.getenv("API_RELOAD", "true").lower() == "true"
        if os.getenv("ENVIRONMENT", "development").lower() == "development"
        else False
    )


class CORSConfig:
    ALLOW_ORIGINS: List[str] = os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
    ALLOW_CREDENTIALS: bool = (
        os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    )
    ALLOW_METHODS: List[str] = os.getenv("CORS_ALLOW_METHODS", "*").split(",")
    ALLOW_HEADERS: List[str] = os.getenv("CORS_ALLOW_HEADERS", "*").split(",")


class AppConfig:
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


db_config = DatabaseConfig()
api_config = APIConfig()
cors_config = CORSConfig()
app_config = AppConfig()

if app_config.is_production:
    api_config.RELOAD = False
