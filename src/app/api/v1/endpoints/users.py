"""User CRUD endpoints (v1)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import UserServiceDep
from app.schemas.common import Page, PageParams
from app.schemas.user import UserCreate, UserPublic, UserUpdate

router = APIRouter()

PageParamsDep = Annotated[PageParams, Depends()]


@router.get(
    "",
    response_model=Page[UserPublic],
    summary="List users",
)
async def list_users(
    page_params: PageParamsDep,
    service: UserServiceDep,
) -> Page[UserPublic]:
    items, total = await service.list(
        offset=page_params.offset,
        limit=page_params.limit,
    )
    return Page[UserPublic](
        items=[UserPublic.model_validate(user) for user in items],
        total=total,
        page=page_params.page,
        size=page_params.size,
    )


@router.post(
    "",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
)
async def create_user(
    payload: UserCreate,
    service: UserServiceDep,
) -> UserPublic:
    user = await service.create(payload)
    return UserPublic.model_validate(user)


@router.get(
    "/{user_id}",
    response_model=UserPublic,
    summary="Retrieve a user by ID",
)
async def get_user(
    user_id: uuid.UUID,
    service: UserServiceDep,
) -> UserPublic:
    user = await service.get(user_id)
    return UserPublic.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserPublic,
    summary="Update a user (partial)",
)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    service: UserServiceDep,
) -> UserPublic:
    user = await service.update(user_id, payload)
    return UserPublic.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
)
async def delete_user(
    user_id: uuid.UUID,
    service: UserServiceDep,
) -> Response:
    await service.delete(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
