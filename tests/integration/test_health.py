"""Integration tests for the health endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app import db as app_db


@pytest.mark.integration
async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "service" in body
    assert "version" in body


@pytest.mark.integration
async def test_readiness(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@pytest.mark.integration
async def test_readiness_reports_503_when_the_database_is_down(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dependency outage must be 503 (retry me), never 500 (I am broken)."""

    async def _boom() -> None:
        raise ConnectionRefusedError("connection refused")

    monkeypatch.setattr(app_db, "ping", _boom)

    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json()["code"] == "service_unavailable"


@pytest.mark.integration
async def test_liveness_does_not_touch_the_database(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Restarting a pod cannot fix a database outage, so liveness must ignore it."""

    async def _boom() -> None:
        raise ConnectionRefusedError("connection refused")

    monkeypatch.setattr(app_db, "ping", _boom)

    assert (await client.get("/api/v1/health")).status_code == 200
