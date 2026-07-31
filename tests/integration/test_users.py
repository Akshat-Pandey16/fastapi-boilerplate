"""Integration tests for the user endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


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
    assert body["errors"] == {"field": "username"}


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
    assert body["has_prev"] is False


@pytest.mark.integration
async def test_pagination_never_repeats_a_row(
    client: AsyncClient, user_payload: dict[str, object]
) -> None:
    """Rows created in the same instant still page deterministically."""
    for idx in range(6):
        response = await client.post(
            "/api/v1/users",
            json={**user_payload, "username": f"user{idx}", "email": f"user{idx}@example.com"},
        )
        assert response.status_code == 201

    seen: list[str] = []
    for page in (1, 2, 3):
        response = await client.get("/api/v1/users", params={"page": page, "size": 2})
        seen.extend(item["id"] for item in response.json()["items"])

    assert len(seen) == len(set(seen)) == 6


@pytest.mark.integration
async def test_update_user(client: AsyncClient, user_payload: dict[str, object]) -> None:
    created = (await client.post("/api/v1/users", json=user_payload)).json()

    response = await client.patch(
        f"/api/v1/users/{created['id']}",
        json={"full_name": "Alice Updated"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Alice Updated"
    assert body["username"] == created["username"]  # untouched fields survive


@pytest.mark.integration
async def test_update_to_a_taken_username_returns_409(
    client: AsyncClient, user_payload: dict[str, object]
) -> None:
    await client.post("/api/v1/users", json=user_payload)
    other = (
        await client.post(
            "/api/v1/users",
            json={"username": "bob", "email": "bob@example.com"},
        )
    ).json()

    response = await client.patch(f"/api/v1/users/{other['id']}", json={"username": "alice"})
    assert response.status_code == 409


@pytest.mark.integration
async def test_update_keeping_the_same_username_is_allowed(
    client: AsyncClient, user_payload: dict[str, object]
) -> None:
    """Re-sending an unchanged unique field must not collide with itself."""
    created = (await client.post("/api/v1/users", json=user_payload)).json()

    response = await client.patch(
        f"/api/v1/users/{created['id']}",
        json={"username": created["username"], "full_name": "Same Name"},
    )
    assert response.status_code == 200


@pytest.mark.integration
async def test_delete_user(client: AsyncClient, user_payload: dict[str, object]) -> None:
    created = (await client.post("/api/v1/users", json=user_payload)).json()

    assert (await client.delete(f"/api/v1/users/{created['id']}")).status_code == 204
    assert (await client.get(f"/api/v1/users/{created['id']}")).status_code == 404
    assert (await client.delete(f"/api/v1/users/{created['id']}")).status_code == 404


@pytest.mark.integration
async def test_get_unknown_user_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/users/{UNKNOWN_ID}")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


@pytest.mark.integration
async def test_invalid_payload_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/users",
        json={"username": "no", "email": "not-an-email"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"
