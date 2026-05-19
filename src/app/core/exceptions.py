"""Domain and HTTP exception hierarchy.

Use ``AppException`` subclasses inside services/repositories — they're caught
by a global handler and translated to ``ProblemDetail`` JSON responses.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any


class AppException(Exception):
    """Base class for all application-level exceptions.

    Attributes mirror RFC 7807 Problem Details so they map cleanly onto the
    JSON response envelope.
    """

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    status_code = HTTPStatus.NOT_FOUND
    code = "not_found"
    message = "Resource not found."


class ConflictError(AppException):
    status_code = HTTPStatus.CONFLICT
    code = "conflict"
    message = "Resource conflict."


class ValidationFailedError(AppException):
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    code = "validation_failed"
    message = "Validation failed."


class AuthenticationError(AppException):
    status_code = HTTPStatus.UNAUTHORIZED
    code = "unauthorized"
    message = "Authentication required."


class AuthorizationError(AppException):
    status_code = HTTPStatus.FORBIDDEN
    code = "forbidden"
    message = "Permission denied."


class RateLimitError(AppException):
    status_code = HTTPStatus.TOO_MANY_REQUESTS
    code = "rate_limited"
    message = "Too many requests."


__all__ = [
    "AppException",
    "AuthenticationError",
    "AuthorizationError",
    "ConflictError",
    "NotFoundError",
    "RateLimitError",
    "ValidationFailedError",
]
