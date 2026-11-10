"""Çalışan profilini geçmiş olayları silmeden yöneten API uçları."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from isg_api.auth import AuthenticatedSession, require_csrf, require_roles
from isg_api.database import get_database_session
from isg_api.management_schemas import ActiveStateRequest, EmployeeWriteRequest
from isg_api.models import (
    Employee,
    FindingAssessment,
    IdentityStatus,
    ReviewStatus,
    SafetyEvent,
    TechnicalStatus,
    UserRole,
)

router = APIRouter(prefix="/api/v1/employees", tags=["Çalışanlar"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]
ManagerAuthentication = Annotated[
    AuthenticatedSession, Depends(require_roles(UserRole.ADMIN, UserRole.ISG))
]
CsrfAuthentication = Annotated[AuthenticatedSession, Depends(require_csrf)]


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_number: str
    full_name: str
    department: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EmployeeEventFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_code: str
    assessment: FindingAssessment
    first_observed_at: datetime
    last_observed_at: datetime
    observation_count: int


class EmployeeEventResponse(BaseModel):
    id: uuid.UUID
    camera_id: uuid.UUID
    camera_name: str
    rule_version_id: uuid.UUID
    identity_status: IdentityStatus
    technical_status: TechnicalStatus
    review_status: ReviewStatus
    started_at: datetime
    last_seen_at: datetime
    ended_at: datetime | None
    source_time_ms: int | None
    model_version: str
    findings: list[EmployeeEventFindingResponse]


class EmployeeHistorySummaryResponse(BaseModel):
    employee_id: uuid.UUID
    total_events: int
    pending_events: int
    confirmed_events: int
    false_alarm_events: int
    last_event_at: datetime | None


def employee_search_pattern(value: str) -> str:
    """LIKE özel karakterlerini metin olarak aramak için güvenle kaçırır."""
    normalized = " ".join(value.split())
    escaped = normalized.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def employee_or_404(database: Session, employee_id: uuid.UUID) -> Employee:
    employee = database.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Çalışan bulunamadı")
    return employee


def commit_employee(database: Session, employee: Employee) -> EmployeeResponse:
    try:
        database.commit()
    except IntegrityError as error:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu çalışan numarası zaten kullanılıyor",
        ) from error
    database.refresh(employee)
    return EmployeeResponse.model_validate(employee)


@router.get("", response_model=list[EmployeeResponse])
def list_employees(
    database: DatabaseSession,
    _authentication: ManagerAuthentication,
    include_inactive: Annotated[bool, Query()] = False,
    q: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EmployeeResponse]:
    statement = select(Employee)
    if not include_inactive:
        statement = statement.where(Employee.is_active.is_(True))
    if q is not None and q.strip():
        pattern = employee_search_pattern(q)
        statement = statement.where(
            or_(
                Employee.employee_number.ilike(pattern, escape="\\"),
                Employee.full_name.ilike(pattern, escape="\\"),
                Employee.department.ilike(pattern, escape="\\"),
            )
        )
    employees = database.scalars(
        statement.order_by(Employee.full_name, Employee.employee_number).offset(offset).limit(limit)
    ).all()
    return [EmployeeResponse.model_validate(employee) for employee in employees]


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: uuid.UUID,
    database: DatabaseSession,
    _authentication: ManagerAuthentication,
) -> EmployeeResponse:
    return EmployeeResponse.model_validate(employee_or_404(database, employee_id))


@router.get("/{employee_id}/events", response_model=list[EmployeeEventResponse])
def list_employee_events(
    employee_id: uuid.UUID,
    database: DatabaseSession,
    _authentication: ManagerAuthentication,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EmployeeEventResponse]:
    employee_or_404(database, employee_id)
    events = database.scalars(
        select(SafetyEvent)
        .options(joinedload(SafetyEvent.camera), selectinload(SafetyEvent.findings))
        .where(SafetyEvent.employee_id == employee_id)
        .order_by(SafetyEvent.started_at.desc(), SafetyEvent.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return [
        EmployeeEventResponse(
            id=event.id,
            camera_id=event.camera_id,
            camera_name=event.camera.name,
            rule_version_id=event.rule_version_id,
            identity_status=event.identity_status,
            technical_status=event.technical_status,
            review_status=event.review_status,
            started_at=event.started_at,
            last_seen_at=event.last_seen_at,
            ended_at=event.ended_at,
            source_time_ms=event.source_time_ms,
            model_version=event.model_version,
            findings=[
                EmployeeEventFindingResponse.model_validate(finding)
                for finding in sorted(event.findings, key=lambda item: item.equipment_code)
            ],
        )
        for event in events
    ]


@router.get("/{employee_id}/history-summary", response_model=EmployeeHistorySummaryResponse)
def get_employee_history_summary(
    employee_id: uuid.UUID,
    database: DatabaseSession,
    _authentication: ManagerAuthentication,
) -> EmployeeHistorySummaryResponse:
    employee_or_404(database, employee_id)
    row = database.execute(
        select(
            func.count(SafetyEvent.id).label("total_events"),
            func.count(SafetyEvent.id)
            .filter(SafetyEvent.review_status == ReviewStatus.PENDING)
            .label("pending_events"),
            func.count(SafetyEvent.id)
            .filter(SafetyEvent.review_status == ReviewStatus.CONFIRMED)
            .label("confirmed_events"),
            func.count(SafetyEvent.id)
            .filter(SafetyEvent.review_status == ReviewStatus.FALSE_ALARM)
            .label("false_alarm_events"),
            func.max(SafetyEvent.started_at).label("last_event_at"),
        ).where(SafetyEvent.employee_id == employee_id)
    ).one()
    return EmployeeHistorySummaryResponse(
        employee_id=employee_id,
        total_events=row.total_events,
        pending_events=row.pending_events,
        confirmed_events=row.confirmed_events,
        false_alarm_events=row.false_alarm_events,
        last_event_at=row.last_event_at,
    )


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeWriteRequest,
    database: DatabaseSession,
    _authentication: ManagerAuthentication,
    _csrf: CsrfAuthentication,
) -> EmployeeResponse:
    employee = Employee(
        employee_number=payload.employee_number,
        full_name=payload.full_name,
        department=payload.department,
    )
    database.add(employee)
    return commit_employee(database, employee)


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: uuid.UUID,
    payload: EmployeeWriteRequest,
    database: DatabaseSession,
    _authentication: ManagerAuthentication,
    _csrf: CsrfAuthentication,
) -> EmployeeResponse:
    employee = employee_or_404(database, employee_id)
    employee.employee_number = payload.employee_number
    employee.full_name = payload.full_name
    employee.department = payload.department
    return commit_employee(database, employee)


@router.patch("/{employee_id}/active", response_model=EmployeeResponse)
def set_employee_active(
    employee_id: uuid.UUID,
    payload: ActiveStateRequest,
    database: DatabaseSession,
    _authentication: ManagerAuthentication,
    _csrf: CsrfAuthentication,
) -> EmployeeResponse:
    employee = employee_or_404(database, employee_id)
    employee.is_active = payload.is_active
    database.commit()
    return EmployeeResponse.model_validate(employee)
