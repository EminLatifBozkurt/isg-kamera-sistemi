"""D2 çekirdek veritabanı modelleri.

Bu tablolar olay anındaki kamera, kural ve kimlik bilgisini tarihsel olarak korur.
Kamera/çalışan kayıtları silinmek yerine pasifleştirileceği için yabancı anahtarlar
geçmişi yanlışlıkla silen CASCADE davranışını kullanmaz.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class CameraSourceType(StrEnum):
    WEBCAM = "webcam"
    RECORDED_VIDEO = "recorded_video"
    RTSP = "rtsp"


class IdentityStatus(StrEnum):
    RECOGNIZED = "recognized"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"


class TechnicalStatus(StrEnum):
    ACTIVE = "active"
    ENDED = "ended"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FALSE_ALARM = "false_alarm"


class FindingAssessment(StrEnum):
    COMPLIANT = "compliant"
    VIOLATION = "violation"
    NOT_EVALUABLE = "not_evaluable"


class MediaType(StrEnum):
    SNAPSHOT = "snapshot"
    CLIP = "clip"


class MediaStatus(StrEnum):
    PREPARING = "preparing"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


class UserRole(StrEnum):
    ADMIN = "admin"
    ISG = "isg"


def value_enum(enum_type: type[StrEnum], name: str, length: int) -> Enum:
    """Python enum adlarını değil kararlı küçük harfli değerleri veritabanına yazar."""
    return Enum(
        enum_type,
        name=name,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda members: [member.value for member in members],
        length=length,
    )


class AppUser(Base):
    __tablename__ = "app_user"
    __table_args__ = (
        CheckConstraint(
            "username = lower(username) AND username ~ '^[a-z0-9][a-z0-9._-]{2,63}$'",
            name="username_format",
        ),
        CheckConstraint("failed_login_count >= 0", name="failed_login_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(value_enum(UserRole, "user_role", 16), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    failed_login_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    sessions: Mapped[list[UserSession]] = relationship(back_populates="user")


class UserSession(Base):
    __tablename__ = "user_session"
    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="absolute_expiry_order"),
        CheckConstraint("idle_expires_at > created_at", name="idle_expiry_order"),
        CheckConstraint("last_seen_at >= created_at", name="last_seen_order"),
        CheckConstraint("verifier_hash ~ '^[0-9a-f]{64}$'", name="verifier_hash_sha256"),
        CheckConstraint("csrf_hash ~ '^[0-9a-f]{64}$'", name="csrf_hash_sha256"),
        Index("ix_user_session_user_expires", "user_id", text("expires_at DESC")),
        Index("ix_user_session_active_expiry", "expires_at", "idle_expires_at"),
    )

    # Kimlik cookie içinde açık taşınabilir; tek başına oturum açmaya yetmez.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False
    )
    # Ham verifier ve CSRF belirteci hiçbir zaman veritabanına yazılmaz.
    verifier_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[AppUser] = relationship(back_populates="sessions")


class EquipmentDefinition(Base):
    __tablename__ = "equipment_definition"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    model_class: Mapped[str | None] = mapped_column(String(80))
    is_model_supported: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Camera(Base):
    __tablename__ = "camera"
    __table_args__ = (
        CheckConstraint("jsonb_typeof(source_config) = 'object'", name="source_config_object"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    source_type: Mapped[CameraSourceType] = mapped_column(
        value_enum(CameraSourceType, "camera_source_type", 24), nullable=False
    )
    source_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    sessions: Mapped[list[CameraSession]] = relationship(back_populates="camera")
    rule_versions: Mapped[list[RuleVersion]] = relationship(back_populates="camera")
    events: Mapped[list[SafetyEvent]] = relationship(back_populates="camera")


class Employee(Base):
    __tablename__ = "employee"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    employee_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    department: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list[SafetyEvent]] = relationship(back_populates="employee")


class CameraSession(Base):
    __tablename__ = "camera_session"
    __table_args__ = (
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="time_order"),
        CheckConstraint(
            "source_start_time_ms IS NULL OR source_start_time_ms >= 0",
            name="source_start_nonnegative",
        ),
        Index("ix_camera_session_camera_started", "camera_id", text("started_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    camera_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("camera.id", ondelete="RESTRICT"), nullable=False
    )
    source_type: Mapped[CameraSourceType] = mapped_column(
        value_enum(CameraSourceType, "session_source_type", 24), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_reason: Mapped[str | None] = mapped_column(String(80))
    source_start_time_ms: Mapped[int | None] = mapped_column(BigInteger)

    camera: Mapped[Camera] = relationship(back_populates="sessions")
    events: Mapped[list[SafetyEvent]] = relationship(back_populates="camera_session")


class RuleVersion(Base):
    __tablename__ = "rule_version"
    __table_args__ = (
        UniqueConstraint("camera_id", "version_number", name="camera_version"),
        UniqueConstraint("camera_id", "definition_hash", name="camera_definition_hash"),
        CheckConstraint("version_number > 0", name="positive_version"),
        CheckConstraint("valid_until IS NULL OR valid_until > valid_from", name="valid_time_order"),
        CheckConstraint("jsonb_typeof(definition) = 'object'", name="definition_object"),
        CheckConstraint("definition_hash ~ '^[0-9a-f]{64}$'", name="definition_hash_sha256"),
        Index("ix_rule_version_camera_valid_from", "camera_id", text("valid_from DESC")),
        Index(
            "uq_rule_version_one_current_per_camera",
            "camera_id",
            unique=True,
            postgresql_where=text("valid_until IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    camera_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("camera.id", ondelete="RESTRICT"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    definition_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    camera: Mapped[Camera] = relationship(back_populates="rule_versions")
    events: Mapped[list[SafetyEvent]] = relationship(back_populates="rule_version")


class SafetyEvent(Base):
    __tablename__ = "safety_event"
    __table_args__ = (
        CheckConstraint("track_id >= 0", name="track_id_nonnegative"),
        CheckConstraint("last_seen_at >= started_at", name="last_seen_order"),
        CheckConstraint("ended_at IS NULL OR ended_at >= last_seen_at", name="ended_order"),
        CheckConstraint(
            "source_time_ms IS NULL OR source_time_ms >= 0", name="source_time_nonnegative"
        ),
        CheckConstraint(
            "(technical_status = 'active' AND ended_at IS NULL) OR "
            "(technical_status = 'ended' AND ended_at IS NOT NULL)",
            name="technical_status_matches_end",
        ),
        CheckConstraint(
            "(identity_status = 'recognized' AND employee_id IS NOT NULL) OR "
            "(identity_status IN ('unknown', 'ambiguous') AND employee_id IS NULL)",
            name="identity_matches_employee",
        ),
        Index("ix_safety_event_camera_started", "camera_id", text("started_at DESC")),
        Index("ix_safety_event_review_started", "review_status", text("started_at DESC")),
        Index("ix_safety_event_employee_started", "employee_id", text("started_at DESC")),
        Index(
            "ix_safety_event_session_track_status",
            "camera_session_id",
            "track_id",
            "technical_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    camera_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("camera.id", ondelete="RESTRICT"), nullable=False
    )
    camera_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("camera_session.id", ondelete="RESTRICT"), nullable=False
    )
    rule_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rule_version.id", ondelete="RESTRICT"), nullable=False
    )
    track_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("employee.id", ondelete="RESTRICT")
    )
    identity_status: Mapped[IdentityStatus] = mapped_column(
        value_enum(IdentityStatus, "identity_status", 16), nullable=False
    )
    technical_status: Mapped[TechnicalStatus] = mapped_column(
        value_enum(TechnicalStatus, "technical_status", 12),
        nullable=False,
        default=TechnicalStatus.ACTIVE,
        server_default=text("'active'"),
    )
    review_status: Mapped[ReviewStatus] = mapped_column(
        value_enum(ReviewStatus, "review_status", 16),
        nullable=False,
        default=ReviewStatus.PENDING,
        server_default=text("'pending'"),
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_time_ms: Mapped[int | None] = mapped_column(BigInteger)
    end_reason: Mapped[str | None] = mapped_column(String(80))
    model_version: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    camera: Mapped[Camera] = relationship(back_populates="events")
    camera_session: Mapped[CameraSession] = relationship(back_populates="events")
    rule_version: Mapped[RuleVersion] = relationship(back_populates="events")
    employee: Mapped[Employee | None] = relationship(back_populates="events")
    findings: Mapped[list[EventFinding]] = relationship(back_populates="event")
    media: Mapped[list[MediaRecord]] = relationship(back_populates="event")
    review_revisions: Mapped[list[EventReviewRevision]] = relationship(back_populates="event")


class EventFinding(Base):
    __tablename__ = "event_finding"
    __table_args__ = (
        UniqueConstraint("event_id", "equipment_code", name="event_equipment"),
        CheckConstraint("observation_count > 0", name="positive_observation_count"),
        CheckConstraint("last_observed_at >= first_observed_at", name="observation_time_order"),
        CheckConstraint("jsonb_typeof(evidence_summary) = 'object'", name="evidence_object"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("safety_event.id", ondelete="CASCADE"), nullable=False
    )
    equipment_code: Mapped[str] = mapped_column(
        ForeignKey("equipment_definition.code", ondelete="RESTRICT"), nullable=False
    )
    assessment: Mapped[FindingAssessment] = mapped_column(
        value_enum(FindingAssessment, "finding_assessment", 20), nullable=False
    )
    first_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    event: Mapped[SafetyEvent] = relationship(back_populates="findings")


class MediaRecord(Base):
    __tablename__ = "media_record"
    __table_args__ = (
        CheckConstraint("size_bytes IS NULL OR size_bytes >= 0", name="size_nonnegative"),
        CheckConstraint("sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$'", name="sha256_format"),
        CheckConstraint(
            "status <> 'ready' OR "
            "(relative_path IS NOT NULL AND mime_type IS NOT NULL AND "
            "size_bytes IS NOT NULL AND sha256 IS NOT NULL AND ready_at IS NOT NULL)",
            name="ready_has_file_metadata",
        ),
        CheckConstraint("status <> 'failed' OR error_message IS NOT NULL", name="failed_has_error"),
        CheckConstraint("status <> 'deleted' OR deleted_at IS NOT NULL", name="deleted_has_time"),
        Index("ix_media_record_event_type", "event_id", "media_type"),
        Index("ix_media_record_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("safety_event.id", ondelete="CASCADE"), nullable=False
    )
    media_type: Mapped[MediaType] = mapped_column(
        value_enum(MediaType, "media_type", 12), nullable=False
    )
    status: Mapped[MediaStatus] = mapped_column(
        value_enum(MediaStatus, "media_status", 12),
        nullable=False,
        default=MediaStatus.PREPARING,
        server_default=text("'preparing'"),
    )
    relative_path: Mapped[str | None] = mapped_column(String(500))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    event: Mapped[SafetyEvent] = relationship(back_populates="media")


class EventReviewRevision(Base):
    __tablename__ = "event_review_revision"
    __table_args__ = (
        UniqueConstraint("event_id", "revision_number", name="event_revision"),
        CheckConstraint("revision_number > 0", name="positive_revision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("safety_event.id", ondelete="CASCADE"), nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_status: Mapped[ReviewStatus | None] = mapped_column(
        value_enum(ReviewStatus, "previous_review_status", 16)
    )
    new_status: Mapped[ReviewStatus] = mapped_column(
        value_enum(ReviewStatus, "new_review_status", 16), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    event: Mapped[SafetyEvent] = relationship(back_populates="review_revisions")
