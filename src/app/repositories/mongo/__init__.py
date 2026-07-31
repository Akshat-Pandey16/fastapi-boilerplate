"""MongoDB-backed repositories.

Requires the ``mongodb`` extra: ``uv sync --extra mongodb``.
"""

from app.repositories.mongo.base import BaseMongoRepository
from app.repositories.mongo.user import MongoUserRepository

__all__ = ["BaseMongoRepository", "MongoUserRepository"]
