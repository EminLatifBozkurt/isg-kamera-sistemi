"""Çalışan profilini geçmiş olayları silmeden yöneten API uçları."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from isg_api.auth import AuthenticatedSession, require_csrf, require_roles
from isg_api.database import get_database_session
from isg_api.management_schemas import ActiveStateRequest, EmployeeWriteRequest
from isg_api.models import Employee, UserRole

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
) -> list[EmployeeResponse]:
    statement = select(Employee)
    if not include_inactive:
        statement = statement.where(Employee.is_active.is_(True))
    employees = database.scalars(
        statement.order_by(Employee.full_name, Employee.employee_number)
    ).all()
    return [EmployeeResponse.model_validate(employee) for employee in employees]


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: uuid.UUID,
    database: DatabaseSession,
    _authentication: ManagerAuthentication,
) -> EmployeeResponse:
    return EmployeeResponse.model_validate(employee_or_404(database, employee_id))


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
