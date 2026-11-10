"""Medya meta bilgisini yalnız yetkili İSG/yönetici oturumuna açar."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from isg_api.auth import AuthenticatedSession, require_roles
from isg_api.database import get_database_session
from isg_api.models import MediaRecord, MediaStatus, MediaType, UserRole

router = APIRouter(prefix="/api/v1/media", tags=["Medya"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]
AuthorizedUser = Annotated[
    AuthenticatedSession, Depends(require_roles(UserRole.ADMIN, UserRole.ISG))
]


class MediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    media_type: MediaType
    status: MediaStatus
    mime_type: str | None
    size_bytes: int | None
    started_at: datetime
    ready_at: datetime | None
    deleted_at: datetime | None


@router.get("/{media_id}", response_model=MediaResponse)
def get_media_metadata(
    media_id: uuid.UUID,
    database: DatabaseSession,
    _authentication: AuthorizedUser,
) -> MediaResponse:
    media = database.get(MediaRecord, media_id)
    if media is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medya bulunamadı")
    return MediaResponse.model_validate(media)
