"""Schemas shared by every resource: pagination, health, error envelope."""

from collections.abc import Sequence
from typing import Annotated, Any

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, computed_field


class ApiModel(BaseModel):
    """Base for response schemas.

    ``from_attributes`` lets ``model_validate`` read domain records directly;
    unknown input keys are dropped rather than rejected, because a response
    model has no business failing on an extra attribute.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore",
    )


class PageParams(BaseModel):
    """Pagination query parameters.

    Inject with ``Annotated[PageParams, Query()]``; FastAPI expands the model
    into individual query parameters and rejects unknown ones.
    """

    model_config = ConfigDict(extra="forbid")

    page: Annotated[int, Query(ge=1, description="1-indexed page number")] = 1
    size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


class Page[T](ApiModel):
    """Paginated response envelope."""

    items: Sequence[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    size: int = Field(ge=1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pages(self) -> int:
        if self.size == 0:
            return 0
        return (self.total + self.size - 1) // self.size

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_prev(self) -> bool:
        return self.page > 1


class HealthResponse(ApiModel):
    """Liveness/readiness payload."""

    status: str = Field(examples=["ok"])
    service: str
    version: str
    environment: str


class ProblemDetail(ApiModel):
    """RFC 7807-style error payload — the shape of every error this API returns."""

    type: str = Field(examples=["about:blank#not_found"])
    title: str = Field(examples=["Not Found"])
    status: int = Field(examples=[404])
    code: str = Field(examples=["not_found"])
    detail: str = Field(examples=["Resource not found."])
    instance: str | None = Field(default=None, examples=["/api/v1/users/123"])
    errors: Any = Field(default=None, description="Field-level details, when the error has any.")


def problem_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """Declare error responses so the docs match what handlers actually return.

    Without this, FastAPI documents its own ``HTTPValidationError`` shape for
    422 and says nothing at all about 404/409/503.
    """
    descriptions = {
        400: "Bad request",
        401: "Authentication required",
        403: "Permission denied",
        404: "Resource not found",
        409: "Conflict with the current state",
        422: "Request validation failed",
        429: "Too many requests",
        500: "Unexpected server error",
        503: "A dependency is unavailable",
    }
    return {
        code: {"model": ProblemDetail, "description": descriptions.get(code, "Error")}
        for code in status_codes
    }


__all__ = [
    "ApiModel",
    "HealthResponse",
    "Page",
    "PageParams",
    "ProblemDetail",
    "problem_responses",
]
