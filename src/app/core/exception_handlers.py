"""FastAPI exception handlers translating errors into RFC 7807-style JSON."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)


def _problem_detail(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    payload: dict[str, Any] = {
        "type": f"about:blank#{code}",
        "title": HTTPStatus(status_code).phrase,
        "status": status_code,
        "code": code,
        "detail": message,
        "instance": str(request.url),
    }
    if details is not None:
        payload["errors"] = jsonable_encoder(details)
    return JSONResponse(status_code=status_code, content=payload)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    logger.warning("app_exception", code=exc.code, message=exc.message, details=exc.details)
    return _problem_detail(
        request=request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details or None,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    logger.warning("http_exception", status=exc.status_code, detail=exc.detail)
    return _problem_detail(
        request=request,
        status_code=exc.status_code,
        code=HTTPStatus(exc.status_code).name.lower(),
        message=str(exc.detail),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.info("validation_error", errors=exc.errors())
    return _problem_detail(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="validation_failed",
        message="Request validation failed.",
        details=exc.errors(),
    )


async def pydantic_validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
    logger.info("pydantic_validation_error", errors=exc.errors())
    return _problem_detail(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="validation_failed",
        message="Data validation failed.",
        details=exc.errors(),
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("integrity_error", error=str(exc.orig))
    return _problem_detail(
        request=request,
        status_code=status.HTTP_409_CONFLICT,
        code="conflict",
        message="A database constraint was violated.",
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("database_error", error=str(exc))
    return _problem_detail(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="database_error",
        message=("A database error occurred." if settings.is_production else str(exc)),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception")
    return _problem_detail(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        message=("An unexpected error occurred." if settings.is_production else str(exc)),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Wire all handlers onto the FastAPI app."""
    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, pydantic_validation_handler)  # type: ignore[arg-type]
    app.add_exception_handler(IntegrityError, integrity_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)


__all__ = ["register_exception_handlers"]
