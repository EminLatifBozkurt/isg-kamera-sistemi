"""Kalıcı olay listesini ve kopma sonrası devam eden WebSocket değişiklik akışını sunar."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from isg_api.auth import AuthenticatedSession, cookie_names, require_csrf, require_roles
from isg_api.database import get_database_session
from isg_api.models import (
    AppUser,
    EventChange,
    EventChangeKind,
    EventReviewRevision,
    IdentityStatus,
    MediaStatus,
    MediaType,
    ReviewStatus,
    SafetyEvent,
    TechnicalStatus,
    UserRole,
    UserSession,
)
from isg_api.security import parse_session_cookie, secret_matches

router = APIRouter(prefix="/api/v1/events", tags=["Olaylar"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]
AuthorizedUser = Annotated[
    AuthenticatedSession, Depends(require_roles(UserRole.ADMIN, UserRole.ISG))
]


class EventMediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    media_type: MediaType
    status: MediaStatus
    mime_type: str | None
    size_bytes: int | None
    error_message: str | None


class EventListItem(BaseModel):
    id: uuid.UUID
    camera_id: uuid.UUID
    camera_name: str
    employee_id: uuid.UUID | None
    employee_name: str | None
    identity_status: IdentityStatus
    technical_status: TechnicalStatus
    review_status: ReviewStatus
    equipment: list[str]
    started_at: datetime
    last_seen_at: datetime
    ended_at: datetime | None
    end_reason: str | None
    media: list[EventMediaResponse]


class EventPage(BaseModel):
    items: list[EventListItem]
    total: int
    offset: int
    limit: int


class EventChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: uuid.UUID
    change_kind: EventChangeKind
    payload: dict[str, object]
    created_at: datetime


class EventChangePage(BaseModel):
    items: list[EventChangeResponse]
    last_id: int
    has_more: bool


class WebSocketMessage(BaseModel):
    type: Literal["event_change", "heartbeat"]
    cursor: int
    change: EventChangeResponse | None = None


class EventReviewRequest(BaseModel):
    new_status: ReviewStatus
    note: str = Field(min_length=2, max_length=2000)

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("İnceleme açıklaması en az iki karakter olmalıdır")
        return normalized


class EventReviewResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    revision_number: int
    previous_status: ReviewStatus | None
    new_status: ReviewStatus
    note: str | None
    reviewed_by: uuid.UUID | None
    reviewed_by_name: str | None
    created_at: datetime


@router.get("", response_model=EventPage)
def list_events(
    database: DatabaseSession,
    _authentication: AuthorizedUser,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> EventPage:
    """Panel yeniden açıldığında kaynağın tamamı olan veritabanından sayfalı liste döner."""
    total = database.scalar(select(func.count(SafetyEvent.id))) or 0
    events = database.scalars(
        select(SafetyEvent)
        .options(
            joinedload(SafetyEvent.camera),
            joinedload(SafetyEvent.employee),
            selectinload(SafetyEvent.findings),
            selectinload(SafetyEvent.media),
        )
        .order_by(SafetyEvent.started_at.desc(), SafetyEvent.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return EventPage(
        items=[_event_response(event) for event in events],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/changes", response_model=EventChangePage)
def list_event_changes(
    database: DatabaseSession,
    _authentication: AuthorizedUser,
    after_id: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
) -> EventChangePage:
    """Bağlantı koparken kaçan değişiklikleri artan sıra numarasıyla tamamlar."""
    changes = database.scalars(
        select(EventChange)
        .where(EventChange.id > after_id)
        .order_by(EventChange.id)
        .limit(limit + 1)
    ).all()
    has_more = len(changes) > limit
    visible = changes[:limit]
    return EventChangePage(
        items=[EventChangeResponse.model_validate(item) for item in visible],
        last_id=visible[-1].id if visible else after_id,
        has_more=has_more,
    )


@router.get("/{event_id}/reviews", response_model=list[EventReviewResponse])
def list_event_reviews(
    event_id: uuid.UUID,
    database: DatabaseSession,
    _authentication: AuthorizedUser,
) -> list[EventReviewResponse]:
    if database.get(SafetyEvent, event_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Olay bulunamadı")
    rows = database.execute(
        select(EventReviewRevision, AppUser.display_name)
        .outerjoin(AppUser, AppUser.id == EventReviewRevision.reviewed_by)
        .where(EventReviewRevision.event_id == event_id)
        .order_by(EventReviewRevision.revision_number)
    ).all()
    return [
        EventReviewResponse(
            id=revision.id,
            event_id=revision.event_id,
            revision_number=revision.revision_number,
            previous_status=revision.previous_status,
            new_status=revision.new_status,
            note=revision.note,
            reviewed_by=revision.reviewed_by,
            reviewed_by_name=reviewer_name,
            created_at=revision.created_at,
        )
        for revision, reviewer_name in rows
    ]


@router.post(
    "/{event_id}/reviews",
    response_model=EventReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_event_review(
    event_id: uuid.UUID,
    payload: EventReviewRequest,
    database: DatabaseSession,
    authentication: Annotated[AuthenticatedSession, Depends(require_csrf)],
) -> EventReviewResponse:
    if authentication.user.role not in {UserRole.ADMIN, UserRole.ISG}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yetkiniz yok")
    # Olay satırı kilidi aynı anda gelen iki kararın aynı sıra numarasını almasını önler.
    event = database.scalar(select(SafetyEvent).where(SafetyEvent.id == event_id).with_for_update())
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Olay bulunamadı")
    latest_revision = database.scalar(
        select(func.max(EventReviewRevision.revision_number)).where(
            EventReviewRevision.event_id == event_id
        )
    )
    revision = EventReviewRevision(
        event_id=event_id,
        revision_number=(latest_revision or 0) + 1,
        previous_status=event.review_status,
        new_status=payload.new_status,
        note=payload.note,
        reviewed_by=authentication.user.id,
    )
    event.review_status = payload.new_status
    database.add(revision)
    database.add(
        EventChange(
            event_id=event_id,
            change_kind=EventChangeKind.EVENT_UPDATED,
            payload={
                "review_status": payload.new_status.value,
                "revision_number": revision.revision_number,
            },
        )
    )
    database.commit()
    database.refresh(revision)
    return EventReviewResponse(
        id=revision.id,
        event_id=revision.event_id,
        revision_number=revision.revision_number,
        previous_status=revision.previous_status,
        new_status=revision.new_status,
        note=revision.note,
        reviewed_by=revision.reviewed_by,
        reviewed_by_name=authentication.user.display_name,
        created_at=revision.created_at,
    )


@router.websocket("/live")
async def live_event_changes(websocket: WebSocket) -> None:
    """Her saniye kalıcı değişiklik tablosunu tarar; Redis gerektirmez."""
    factory = getattr(websocket.app.state, "database_session_factory", None)
    if factory is None:
        await websocket.close(code=1013, reason="Veritabanı hazır değil")
        return
    try:
        cursor = int(websocket.query_params.get("after_id", "0"))
        if cursor < 0:
            raise ValueError
    except ValueError:
        await websocket.close(code=1008, reason="after_id geçersiz")
        return

    if not _websocket_is_authorized(websocket, factory):
        await websocket.close(code=4401, reason="Oturum geçersiz veya süresi dolmuş")
        return

    await websocket.accept()
    idle_rounds = 0
    try:
        while True:
            with factory() as database:
                changes = database.scalars(
                    select(EventChange)
                    .where(EventChange.id > cursor)
                    .order_by(EventChange.id)
                    .limit(100)
                ).all()
            if changes:
                idle_rounds = 0
                for change in changes:
                    cursor = change.id
                    response = EventChangeResponse.model_validate(change)
                    await websocket.send_json(
                        WebSocketMessage(
                            type="event_change", cursor=cursor, change=response
                        ).model_dump(mode="json")
                    )
                continue

            idle_rounds += 1
            if idle_rounds >= 15:
                await websocket.send_json(
                    WebSocketMessage(type="heartbeat", cursor=cursor).model_dump(mode="json")
                )
                idle_rounds = 0
            try:
                message = await asyncio.wait_for(websocket.receive(), timeout=1.0)
                if message["type"] == "websocket.disconnect":
                    return
            except TimeoutError:
                pass
    except WebSocketDisconnect:
        return


def _event_response(event: SafetyEvent) -> EventListItem:
    return EventListItem(
        id=event.id,
        camera_id=event.camera_id,
        camera_name=event.camera.name,
        employee_id=event.employee_id,
        employee_name=event.employee.full_name if event.employee else None,
        identity_status=event.identity_status,
        technical_status=event.technical_status,
        review_status=event.review_status,
        equipment=sorted(item.equipment_code for item in event.findings),
        started_at=event.started_at,
        last_seen_at=event.last_seen_at,
        ended_at=event.ended_at,
        end_reason=event.end_reason,
        media=[
            EventMediaResponse.model_validate(item)
            for item in sorted(event.media, key=lambda item: item.media_type.value)
        ],
    )


def _websocket_is_authorized(websocket: WebSocket, factory) -> bool:
    settings = websocket.app.state.settings
    session_name, _csrf_name = cookie_names(settings)
    parsed = parse_session_cookie(websocket.cookies.get(session_name))
    if parsed is None:
        return False
    session_id, verifier = parsed
    with factory() as database:
        server_session = database.scalar(
            select(UserSession)
            .options(joinedload(UserSession.user))
            .where(UserSession.id == session_id)
        )
        if server_session is None or not secret_matches(verifier, server_session.verifier_hash):
            return False
        now = datetime.now(UTC)
        expired = now >= server_session.expires_at or now >= server_session.idle_expires_at
        allowed_role = server_session.user.role in {UserRole.ADMIN, UserRole.ISG}
        valid = (
            server_session.revoked_at is None
            and not expired
            and server_session.user.is_active
            and allowed_role
        )
        if valid:
            server_session.last_seen_at = now
            server_session.idle_expires_at = min(
                server_session.expires_at,
                now + timedelta(minutes=settings.session_idle_minutes),
            )
            database.commit()
        return valid
