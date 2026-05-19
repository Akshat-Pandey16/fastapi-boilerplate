"""Liveness and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status
from sqlalchemy import text

from app.api.deps import SessionDep
from app.core.config import settings
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
)
async def liveness() -> HealthResponse:
    """Return basic service metadata without checking dependencies."""
    return HealthResponse(
        status="ok",
        service=settings.api_title,
        version=settings.api_version,
        environment=settings.environment.value,
    )


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
)
async def readiness(session: SessionDep) -> HealthResponse:
    """Verify downstream dependencies (DB) before reporting ready."""
    await session.execute(text("SELECT 1"))
    return HealthResponse(
        status="ready",
        service=settings.api_title,
        version=settings.api_version,
        environment=settings.environment.value,
    )
