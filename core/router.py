from fastapi import APIRouter

from api.users import router as user_router

router = APIRouter(prefix="/api/v1")
router.include_router(user_router, prefix="/users")
