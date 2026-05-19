"""Integration tests for the user endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.fixture
def user_payload() -> dict[str, object]:
    return {
        "username": "alice",
        "email": "alice@example.com",
        "full_name": "Alice Example",
    }


@pytest.mark.integration
async def test_create_and_fetch_user(client: AsyncClient, user_payload: dict[str, object]) -> None:
    create = await client.post("/api/v1/users", json=user_payload)
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["username"] == user_payload["username"]
    assert body["email"] == user_payload["email"]
    user_id = body["id"]

    fetch = await client.get(f"/api/v1/users/{user_id}")
    assert fetch.status_code == 200
    assert fetch.json()["id"] == user_id


@pytest.mark.integration
async def test_create_duplicate_username_returns_409(
    client: AsyncClient, user_payload: dict[str, object]
) -> None:
    first = await client.post("/api/v1/users", json=user_payload)
    assert first.status_code == 201

    duplicate = await client.post(
        "/api/v1/users",
        json={**user_payload, "email": "other@example.com"},
    )
    assert duplicate.status_code == 409
    body = duplicate.json()
    assert body["code"] == "conflict"


@pytest.mark.integration
async def test_list_users_pagination(client: AsyncClient, user_payload: dict[str, object]) -> None:
    for idx in range(3):
        payload = {
            **user_payload,
            "username": f"user_{idx}",
            "email": f"user_{idx}@example.com",
        }
        response = await client.post("/api/v1/users", json=payload)
        assert response.status_code == 201

    page = await client.get("/api/v1/users", params={"page": 1, "size": 2})
    assert page.status_code == 200
    body = page.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["pages"] == 2
    assert body["has_next"] is True


@pytest.mark.integration
async def test_get_unknown_user_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
