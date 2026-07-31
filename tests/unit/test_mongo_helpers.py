"""Unit tests for MongoDB storage quirks that need no server."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

pytest.importorskip("pymongo", reason="the mongodb extra is not installed")

from app.repositories.mongo.base import BaseMongoRepository, bson_utcnow


@pytest.mark.unit
def test_bson_utcnow_is_millisecond_precise() -> None:
    """BSON drops sub-millisecond digits.

    If a repository returned a microsecond-precision value it would not match
    the value the next read gets back, and a freshly created document would
    appear to change on its own.
    """
    now = bson_utcnow()
    assert now.microsecond % 1000 == 0
    assert now.tzinfo is UTC


@pytest.mark.unit
def test_documents_come_back_with_a_plain_utc_timezone() -> None:
    """The driver hands back bson's FixedOffset; the domain layer wants UTC."""
    bson_utc = timezone(timedelta(0), "UTC")  # what pymongo attaches
    stored = datetime(2026, 7, 31, 12, 0, 0, tzinfo=bson_utc)

    values = BaseMongoRepository._from_document({"_id": 1, "created_at": stored})

    assert values["id"] == 1
    assert values["created_at"].tzinfo is UTC
    assert values["created_at"] == stored  # same instant, normalised representation


@pytest.mark.unit
def test_id_is_mapped_to_mongos_primary_key() -> None:
    assert BaseMongoRepository._to_document({"id": 7, "name": "x"}) == {"_id": 7, "name": "x"}
