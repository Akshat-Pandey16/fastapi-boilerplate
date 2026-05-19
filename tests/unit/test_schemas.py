"""Unit tests for Pydantic schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.common import Page
from app.schemas.user import UserCreate


@pytest.mark.unit
def test_user_create_rejects_invalid_username() -> None:
    with pytest.raises(ValidationError):
        UserCreate(username="ab", email="a@b.com")


@pytest.mark.unit
def test_user_create_accepts_minimal_payload() -> None:
    user = UserCreate(username="alice", email="alice@example.com")
    assert user.is_active is True
    assert user.is_superuser is False


@pytest.mark.unit
def test_page_computes_metadata() -> None:
    page = Page[int](items=[1, 2, 3], total=7, page=1, size=3)
    assert page.pages == 3
    assert page.has_next is True
    assert page.has_prev is False
