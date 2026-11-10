"""Kamera kayıtlarını silmeden yöneten API uçları."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from isg_api.auth import AuthenticatedSession, require_csrf, require_roles
from isg_api.database import get_database_session
from isg_api.management_schemas import ActiveStateRequest, CameraWriteRequest
from isg_api.models import Camera, CameraSourceType, UserRole

router = APIRouter(prefix="/api/v1/cameras", tags=["Kameralar"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]
ManagerAuthentication = Annotated[
    AuthenticatedSession, Depends(require_roles(UserRole.ADMIN, UserRole.ISG))
]
CsrfAuthentication = Annotated[AuthenticatedSession, Depends(require_csrf)]


class CameraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    source_type: CameraSourceType
    source_config: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime


def camera_or_404(database: Session, camera_id: uuid.UUID) -> Camera:
    camera = database.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kamera bulunamadı")
    return camera


def commit_camera(database: Session, camera: Camera) -> CameraResponse:
    try:
        database.commit()
    except IntegrityError as error:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu kamera adı zaten kullanılıyor",
        ) from error
    database.refresh(camera)
    return CameraResponse.model_validate(camera)


@router.get("", response_model=list[CameraResponse])
def list_cameras(
    database: DatabaseSession,
    _authentication: ManagerAuthentication,
    include_inactive: Annotated[bool, Query()] = False,
) -> list[CameraResponse]:
    statement = select(Camera)
    if not include_inactive:
        statement = statement.where(Camera.is_active.is_(True))
    cameras = database.scalars(statement.order_by(Camera.name)).all()
    return [CameraResponse.model_validate(camera) for camera in cameras]


@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(
    camera_id: uuid.UUID,
    database: DatabaseSession,
    _authentication: ManagerAuthentication,
) -> CameraResponse:
    return CameraResponse.model_validate(camera_or_404(database, camera_id))


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
def create_camera(
    payload: CameraWriteRequest,
    database: DatabaseSession,
    _authentication: ManagerAuthentication,
    _csrf: CsrfAuthentication,
) -> CameraResponse:
    camera = Camera(
        name=payload.name,
        source_type=payload.source_type,
        source_config=payload.source_config,
    )
    database.add(camera)
    return commit_camera(database, camera)


@router.put("/{camera_id}", response_model=CameraResponse)
def update_camera(
    camera_id: uuid.UUID,
    payload: CameraWriteRequest,
    database: DatabaseSession,
    _authentication: ManagerAuthentication,
    _csrf: CsrfAuthentication,
) -> CameraResponse:
    camera = camera_or_404(database, camera_id)
    camera.name = payload.name
    camera.source_type = payload.source_type
    camera.source_config = payload.source_config
    return commit_camera(database, camera)


@router.patch("/{camera_id}/active", response_model=CameraResponse)
def set_camera_active(
    camera_id: uuid.UUID,
    payload: ActiveStateRequest,
    database: DatabaseSession,
    _authentication: ManagerAuthentication,
    _csrf: CsrfAuthentication,
) -> CameraResponse:
    camera = camera_or_404(database, camera_id)
    camera.is_active = payload.is_active
    database.commit()
    return CameraResponse.model_validate(camera)
