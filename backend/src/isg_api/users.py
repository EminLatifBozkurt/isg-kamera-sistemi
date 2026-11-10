"""Yalnız yöneticiye açık kullanıcı ve rol yönetimi API'si."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from isg_api.auth import (
    AuthenticatedSession,
    UserResponse,
    require_csrf,
    require_roles,
)
from isg_api.database import get_database_session
from isg_api.models import AppUser, UserRole, UserSession
from isg_api.security import hash_password, normalize_username

router = APIRouter(prefix="/api/v1/users", tags=["Kullanıcılar"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]
AdminAuthentication = Annotated[AuthenticatedSession, Depends(require_roles(UserRole.ADMIN))]
CsrfAuthentication = Annotated[AuthenticatedSession, Depends(require_csrf)]


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=2, max_length=160)
    password: SecretStr
    role: UserRole


class SetUserActiveRequest(BaseModel):
    is_active: bool


@router.get("", response_model=list[UserResponse])
def list_users(
    database: DatabaseSession,
    _authentication: AdminAuthentication,
) -> list[UserResponse]:
    users = database.scalars(select(AppUser).order_by(AppUser.username)).all()
    return [UserResponse.model_validate(user) for user in users]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CreateUserRequest,
    database: DatabaseSession,
    _authentication: AdminAuthentication,
    _csrf: CsrfAuthentication,
) -> UserResponse:
    try:
        username = normalize_username(payload.username)
        password_hash = hash_password(payload.password.get_secret_value())
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error

    display_name = payload.display_name.strip()
    if len(display_name) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Görünen ad en az 2 karakter olmalıdır",
        )

    user = AppUser(
        username=username,
        display_name=display_name,
        password_hash=password_hash,
        role=payload.role,
    )
    database.add(user)
    try:
        database.commit()
    except IntegrityError as error:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu kullanıcı adı zaten kayıtlı",
        ) from error
    database.refresh(user)
    return UserResponse.model_validate(user)


@router.patch("/{user_id}/active", response_model=UserResponse)
def set_user_active(
    user_id: uuid.UUID,
    payload: SetUserActiveRequest,
    database: DatabaseSession,
    authentication: AdminAuthentication,
    _csrf: CsrfAuthentication,
) -> UserResponse:
    user = database.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı")
    if user.id == authentication.user.id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Yönetici kendi hesabını pasifleştiremez",
        )

    user.is_active = payload.is_active
    if not payload.is_active:
        database.execute(
            update(UserSession)
            .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
    database.commit()
    return UserResponse.model_validate(user)
