from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from models.user import User
from schemas.user import UserCreate, UserList, UserResponse, UserUpdate
from utils.response_helpers import ApiHelpers

router = APIRouter(tags=["Users"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)) -> Any:
    try:
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            is_active=user_data.is_active,
            is_superuser=user_data.is_superuser,
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return ApiHelpers.endpointResponse(
            status_code=201,
            message="User created successfully",
            data=db_user,
        )
    except IntegrityError:
        return ApiHelpers.endpointResponse(
            status_code=400,
            message="User already exists",
        )
    except Exception as e:
        return ApiHelpers.endpointResponse(
            status_code=500,
            message=str(e),
        )


@router.get("/", response_model=UserList, status_code=200)
async def get_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    try:
        offset = (page - 1) * per_page
        query = select(User).offset(offset).limit(per_page)
        result = await db.execute(query)
        users = result.scalars().all()
        total = await db.scalar(select(func.count(User.id)))
        return ApiHelpers.endpointResponse(
            status_code=200,
            message="Users fetched successfully",
            data=users,
            total=total,
            page=page,
            per_page=per_page,
        )
    except Exception as e:
        return ApiHelpers.endpointResponse(
            status_code=500,
            message=str(e),
        )


@router.get("/{user_id}", response_model=UserResponse, status_code=200)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    try:
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return ApiHelpers.endpointResponse(
                status_code=404,
                message="User not found",
            )
        return ApiHelpers.endpointResponse(
            status_code=200,
            message="User fetched successfully",
            data=user,
        )
    except Exception as e:
        return ApiHelpers.endpointResponse(
            status_code=500,
            message=str(e),
        )


@router.put("/{user_id}", response_model=UserResponse, status_code=200)
async def update_user(
    user_id: int, user_data: UserUpdate, db: AsyncSession = Depends(get_db)
) -> Any:
    try:
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return ApiHelpers.endpointResponse(
                status_code=404,
                message="User not found",
            )
        for field, value in user_data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        await db.commit()
        await db.refresh(user)
        return ApiHelpers.endpointResponse(
            status_code=200,
            message="User updated successfully",
            data=user,
        )
    except Exception as e:
        return ApiHelpers.endpointResponse(
            status_code=500,
            message=str(e),
        )


@router.delete("/{user_id}", status_code=200)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    try:
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return ApiHelpers.endpointResponse(
                status_code=404,
                message="User not found",
            )
        await db.delete(user)
        await db.commit()
        return ApiHelpers.endpointResponse(
            status_code=200,
            message="User deleted successfully",
        )
    except Exception as e:
        return ApiHelpers.endpointResponse(
            status_code=500,
            message=str(e),
        )
