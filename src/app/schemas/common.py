"""Cross-cutting Pydantic schemas: pagination, envelope, error format."""

from collections.abc import Sequence
from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, computed_field


class _CamelModel(BaseModel):
    """Base model with project-wide ConfigDict (ORM-friendly, strict)."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore",
    )


class PageParams(BaseModel):
    """Reusable pagination query parameters.

    Inject via ``Annotated[PageParams, Depends()]`` on endpoints.
    """

    page: Annotated[int, Query(ge=1, description="1-indexed page number")] = 1
    size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


class Page[T](_CamelModel):
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


class HealthResponse(_CamelModel):
    """Liveness/readiness payload."""

    status: str = Field(examples=["ok"])
    service: str
    version: str
    environment: str


class ProblemDetail(_CamelModel):
    """RFC 7807-style error payload."""

    type: str = Field(examples=["about:blank#not_found"])
    title: str = Field(examples=["Not Found"])
    status: int = Field(examples=[404])
    code: str = Field(examples=["not_found"])
    detail: str = Field(examples=["Resource not found."])
    instance: str | None = Field(default=None, examples=["/api/v1/users/123"])
    errors: list[dict[str, object]] | None = None


__all__ = ["HealthResponse", "Page", "PageParams", "ProblemDetail"]
