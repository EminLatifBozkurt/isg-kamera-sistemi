"""Sabit ekipman kataloğu ve değiştirilemez kamera kural sürümleri API'si."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from isg_api.auth import AuthenticatedSession, require_csrf, require_roles
from isg_api.database import get_database_session
from isg_api.management_schemas import (
    RuleDefinitionRequest,
    canonical_rule_definition,
    rule_definition_hash,
)
from isg_api.models import Camera, EquipmentDefinition, RuleVersion, UserRole

router = APIRouter(prefix="/api/v1", tags=["Kamera kuralları"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]
ManagerAuthentication = Annotated[
    AuthenticatedSession, Depends(require_roles(UserRole.ADMIN, UserRole.ISG))
]
CsrfAuthentication = Annotated[AuthenticatedSession, Depends(require_csrf)]


class EquipmentDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    display_name: str
    model_class: str | None
    is_model_supported: bool


class RuleVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    camera_id: uuid.UUID
    version_number: int
    valid_from: datetime
    valid_until: datetime | None
    definition: dict[str, Any]
    definition_hash: str
    created_by: uuid.UUID | None
    created_at: datetime


@router.get("/equipment", response_model=list[EquipmentDefinitionResponse])
def list_equipment(
    database: DatabaseSession,
    _authentication: ManagerAuthentication,
) -> list[EquipmentDefinitionResponse]:
    equipment = database.scalars(
        select(EquipmentDefinition).order_by(EquipmentDefinition.display_name)
    ).all()
    return [EquipmentDefinitionResponse.model_validate(item) for item in equipment]


@router.get("/cameras/{camera_id}/rules", response_model=list[RuleVersionResponse])
def list_rule_versions(
    camera_id: uuid.UUID,
    database: DatabaseSession,
    _authentication: ManagerAuthentication,
) -> list[RuleVersionResponse]:
    if database.get(Camera, camera_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kamera bulunamadı")
    rules = database.scalars(
        select(RuleVersion)
        .where(RuleVersion.camera_id == camera_id)
        .order_by(RuleVersion.version_number.desc())
    ).all()
    return [RuleVersionResponse.model_validate(rule) for rule in rules]


@router.get("/cameras/{camera_id}/rules/current", response_model=RuleVersionResponse)
def get_current_rule(
    camera_id: uuid.UUID,
    database: DatabaseSession,
    _authentication: ManagerAuthentication,
) -> RuleVersionResponse:
    rule = database.scalar(
        select(RuleVersion).where(
            RuleVersion.camera_id == camera_id,
            RuleVersion.valid_until.is_(None),
        )
    )
    if rule is None:
        if database.get(Camera, camera_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kamera bulunamadı")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kameranın etkin kuralı bulunamadı",
        )
    return RuleVersionResponse.model_validate(rule)


@router.post(
    "/cameras/{camera_id}/rules",
    response_model=RuleVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_rule_version(
    camera_id: uuid.UUID,
    payload: RuleDefinitionRequest,
    database: DatabaseSession,
    authentication: ManagerAuthentication,
    _csrf: CsrfAuthentication,
) -> RuleVersionResponse:
    # Kamera satırını kilitlemek, aynı anda iki isteğin aynı sürüm numarasını
    # üretmesini engeller. Eski kural satırı hiçbir zaman güncellenip ezilmez.
    camera = database.scalar(select(Camera).where(Camera.id == camera_id).with_for_update())
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kamera bulunamadı")

    definition = canonical_rule_definition(payload)
    definition_hash = rule_definition_hash(definition)
    current_rule = database.scalar(
        select(RuleVersion)
        .where(RuleVersion.camera_id == camera_id, RuleVersion.valid_until.is_(None))
        .with_for_update()
    )
    if current_rule is not None and current_rule.definition_hash == definition_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu kural tanımı zaten etkin",
        )

    next_version = (
        database.scalar(
            select(func.max(RuleVersion.version_number)).where(RuleVersion.camera_id == camera_id)
        )
        or 0
    ) + 1
    now = datetime.now(UTC)
    if current_rule is not None:
        if now <= current_rule.valid_from:
            now = current_rule.valid_from + timedelta(microseconds=1)
        current_rule.valid_until = now

    new_rule = RuleVersion(
        camera_id=camera_id,
        version_number=next_version,
        valid_from=now,
        definition=definition,
        definition_hash=definition_hash,
        created_by=authentication.user.id,
    )
    database.add(new_rule)
    try:
        database.commit()
    except IntegrityError as error:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kural aynı anda başka bir işlem tarafından değiştirildi",
        ) from error
    database.refresh(new_rule)
    return RuleVersionResponse.model_validate(new_rule)
