import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.config import api_config, app_config, cors_config
from core.router import router as api_router
from schemas import HealthResponse

logging.basicConfig(
    level=getattr(logging, app_config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app.log")
        if app_config.is_production
        else logging.NullHandler(),
    ],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {api_config.TITLE} v{api_config.VERSION}")
    logger.info(f"Environment: {app_config.ENVIRONMENT}")
    logger.info(f"Log level: {app_config.LOG_LEVEL}")

    yield

    logger.info(f"Shutting down {api_config.TITLE}")


app = FastAPI(
    title=api_config.TITLE,
    description=api_config.DESCRIPTION,
    version=api_config.VERSION,
    docs_url="/docs" if app_config.is_development else None,
    redoc_url="/redoc" if app_config.is_development else None,
    lifespan=lifespan,
)


def create_error_response(
    error_type: str, message: str, status_code: int, path: str, details: Any = None
) -> Dict[str, Any]:
    return {
        "error": error_type,
        "message": message,
        "status_code": status_code,
        "path": path,
        "details": details,
        "timestamp": datetime.now().isoformat(),
    }


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            "HTTP Error",
            exc.detail,
            exc.status_code,
            request.url.path,
        ),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_error_response(
            "Validation Error",
            "Request validation failed",
            422,
            request.url.path,
            exc.errors(),
        ),
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    logger.warning(f"Pydantic Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_error_response(
            "Validation Error",
            "Data validation failed",
            422,
            request.url.path,
            exc.errors(),
        ),
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    logger.error(f"Database Error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            "Database Error",
            "A database error occurred" if app_config.is_production else str(exc),
            500,
            request.url.path,
        ),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            "Internal Server Error",
            "An unexpected error occurred" if app_config.is_production else str(exc),
            500,
            request.url.path,
        ),
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        logger.info(
            f"Response: {request.method} {request.url.path} - {response.status_code}"
        )
        return response
    except Exception as e:
        logger.error(f"Request failed: {request.method} {request.url.path} - {str(e)}")
        raise


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config.ALLOW_ORIGINS,
    allow_credentials=cors_config.ALLOW_CREDENTIALS,
    allow_methods=cors_config.ALLOW_METHODS,
    allow_headers=cors_config.ALLOW_HEADERS,
)

app.include_router(api_router)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service=api_config.TITLE,
        version=api_config.VERSION,
        environment=app_config.ENVIRONMENT,
    )


@app.get("/", response_model=Dict[str, Any])
async def root() -> Dict[str, Any]:
    try:
        return {
            "message": f"Welcome to {api_config.TITLE}",
            "version": api_config.VERSION,
            "environment": app_config.ENVIRONMENT,
            "docs": (
                "/docs"
                if app_config.is_development
                else "Documentation disabled in production"
            ),
            "redoc": "/redoc" if app_config.is_development else None,
            "health": "/health",
        }
    except Exception as e:
        logger.error(f"Error in root endpoint: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        uvicorn.run(
            "main:app",
            host=api_config.HOST,
            port=api_config.PORT,
            reload=api_config.RELOAD,
            reload_dirs=["api", "core"],
            log_level=app_config.LOG_LEVEL.lower(),
        )
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        sys.exit(1)
