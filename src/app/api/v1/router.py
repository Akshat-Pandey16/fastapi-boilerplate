"""API v1 router — aggregates all v1 endpoint routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, users

router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(users.router, prefix="/users", tags=["users"])

__all__ = ["router"]
