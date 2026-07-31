"""Liveness and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status

from app import db
from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import get_logger
from app.schemas.common import HealthResponse, problem_responses

logger = get_logger(__name__)

router = APIRouter()


def _payload(state: str) -> HealthResponse:
    return HealthResponse(
        status=state,
        service=settings.api_title,
        version=settings.api_version,
        environment=settings.environment.value,
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
)
async def liveness() -> HealthResponse:
    """Report that the process is up, without touching any dependency.

    Keep it dependency-free: an orchestrator restarts the container when this
    fails, and restarting never fixes a database outage.
    """
    return _payload("ok")


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    responses=problem_responses(503),
)
async def readiness() -> HealthResponse:
    """Report whether the service can serve traffic — i.e. the database answers."""
    try:
        await db.ping()
    except Exception as exc:
        logger.warning("readiness_failed", error=str(exc))
        raise ServiceUnavailableError(message="Database is unreachable.") from exc
    return _payload("ready")
