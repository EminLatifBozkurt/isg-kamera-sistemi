"""E2 olay geçişlerini ve E3 medya sonucunu atomik PostgreSQL kayıtlarına çevirir."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from isg_api.event_lifecycle import EventTransition, EventTransitionKind
from isg_api.evidence_capture import EvidenceJobSnapshot, EvidenceStatus
from isg_api.models import (
    CameraSession,
    EventChange,
    EventChangeKind,
    EventFinding,
    FindingAssessment,
    IdentityStatus,
    MediaRecord,
    MediaStatus,
    MediaType,
    RuleVersion,
    SafetyEvent,
    TechnicalStatus,
)


@dataclass(frozen=True, slots=True)
class EventPersistenceContext:
    camera_id: uuid.UUID
    identity_status: IdentityStatus
    employee_id: uuid.UUID | None
    model_version: str

    def __post_init__(self) -> None:
        if (self.identity_status is IdentityStatus.RECOGNIZED) != (self.employee_id is not None):
            raise ValueError("Tanınmış kimlik ile çalışan bağlantısı birlikte bulunmalıdır")
        if not self.model_version.strip() or len(self.model_version) > 120:
            raise ValueError("Model sürümü 1-120 karakter olmalıdır")


def persist_event_transition(
    database: Session,
    transition: EventTransition,
    context: EventPersistenceContext,
) -> SafetyEvent:
    """Geçişi yazar; commit çağrısı analiz işlem sınırının sorumluluğundadır."""
    camera_session = database.get(CameraSession, transition.key.camera_session_id)
    rule_version = database.get(RuleVersion, transition.key.rule_version_id)
    if camera_session is None:
        raise ValueError("Olayın kamera oturumu veritabanında bulunamadı")
    if rule_version is None:
        raise ValueError("Olayın kural sürümü veritabanında bulunamadı")
    if camera_session.camera_id != context.camera_id or rule_version.camera_id != context.camera_id:
        raise ValueError("Olayın kamera, oturum ve kural bağlantıları uyuşmuyor")

    event = database.get(SafetyEvent, transition.event_id)
    if transition.kind is EventTransitionKind.STARTED:
        if event is not None:
            _validate_existing_event(event, transition, context)
            return event
        started_at = _source_datetime(camera_session, transition.started_at_seconds)
        event = SafetyEvent(
            id=transition.event_id,
            camera_id=context.camera_id,
            camera_session_id=transition.key.camera_session_id,
            rule_version_id=transition.key.rule_version_id,
            track_id=transition.key.track_id,
            employee_id=context.employee_id,
            identity_status=context.identity_status,
            technical_status=TechnicalStatus.ACTIVE,
            started_at=started_at,
            last_seen_at=started_at,
            source_time_ms=round(transition.started_at_seconds * 1000),
            model_version=context.model_version.strip(),
        )
        database.add(event)
        for equipment in transition.observed_equipment:
            database.add(
                EventFinding(
                    event_id=event.id,
                    equipment_code=equipment.value,
                    assessment=FindingAssessment.VIOLATION,
                    first_observed_at=started_at,
                    last_observed_at=started_at,
                    observation_count=1,
                    evidence_summary={"source": "temporal_policy"},
                )
            )
        database.add_all(
            [
                MediaRecord(event_id=event.id, media_type=MediaType.SNAPSHOT),
                MediaRecord(event_id=event.id, media_type=MediaType.CLIP),
            ]
        )
        _add_change(
            database,
            event.id,
            EventChangeKind.EVENT_STARTED,
            {
                "camera_id": str(context.camera_id),
                "identity_status": context.identity_status.value,
                "employee_id": str(context.employee_id) if context.employee_id else None,
                "equipment": sorted(item.value for item in transition.observed_equipment),
            },
        )
        database.flush()
        return event

    if event is None:
        raise ValueError("Başlangıç kaydı olmayan olay güncellenemez")
    _validate_existing_event(event, transition, context)
    if event.technical_status is TechnicalStatus.ENDED:
        # Aynı bitiş komutunun güvenli tekrarına izin ver, bitmiş olayı değiştirme.
        if transition.kind is EventTransitionKind.ENDED:
            if transition.ended_at_seconds is None or transition.end_reason is None:
                raise ValueError("Bitiş geçişinde zaman ve neden zorunludur")
            expected_end = _source_datetime(camera_session, transition.ended_at_seconds)
            if event.ended_at != expected_end or event.end_reason != transition.end_reason.value:
                raise ValueError("Tekrarlanan olay bitiş komutu kalıcı kayıtla uyuşmuyor")
            return event
        raise ValueError("Bitmiş olay yeniden güncellenemez")

    observed_at = _source_datetime(camera_session, transition.last_seen_at_seconds)
    event.last_seen_at = observed_at
    findings = {item.equipment_code: item for item in event.findings}
    new_equipment: list[str] = []
    current_codes = {item.value for item in transition.current_equipment}
    for equipment in transition.observed_equipment:
        finding = findings.get(equipment.value)
        if finding is None:
            finding = EventFinding(
                event_id=event.id,
                equipment_code=equipment.value,
                assessment=FindingAssessment.VIOLATION,
                first_observed_at=observed_at,
                last_observed_at=observed_at,
                observation_count=1,
                evidence_summary={"source": "temporal_policy"},
            )
            database.add(finding)
            findings[equipment.value] = finding
            new_equipment.append(equipment.value)
        elif equipment.value in current_codes:
            finding.last_observed_at = observed_at
            finding.observation_count += 1

    if new_equipment:
        _add_change(
            database,
            event.id,
            EventChangeKind.EVENT_UPDATED,
            {"new_equipment": sorted(new_equipment)},
        )

    if transition.kind is EventTransitionKind.ENDED:
        if transition.ended_at_seconds is None or transition.end_reason is None:
            raise ValueError("Bitiş geçişinde zaman ve neden zorunludur")
        event.technical_status = TechnicalStatus.ENDED
        event.ended_at = _source_datetime(camera_session, transition.ended_at_seconds)
        event.end_reason = transition.end_reason.value
        _add_change(
            database,
            event.id,
            EventChangeKind.EVENT_ENDED,
            {"end_reason": transition.end_reason.value},
        )
    database.flush()
    return event


def persist_evidence_job(
    database: Session,
    job: EvidenceJobSnapshot,
    *,
    ready_at: datetime,
) -> tuple[MediaRecord, MediaRecord]:
    """E3 sonucunu iki medya satırına uygular; preparing işi henüz değiştirmez."""
    records = database.scalars(
        select(MediaRecord).where(MediaRecord.event_id == job.event_id)
    ).all()
    by_type = {record.media_type: record for record in records}
    if set(by_type) != {MediaType.SNAPSHOT, MediaType.CLIP}:
        raise ValueError("Olayın fotoğraf ve klip hazırlık kayıtları bulunamadı")
    snapshot, clip = by_type[MediaType.SNAPSHOT], by_type[MediaType.CLIP]
    if job.status is EvidenceStatus.PREPARING:
        return snapshot, clip
    if job.status is EvidenceStatus.READY:
        if job.result is None:
            raise ValueError("Hazır kanıt işinde dosya sonucu bulunmalıdır")
        _mark_media_ready(snapshot, job.result.snapshot, ready_at)
        _mark_media_ready(clip, job.result.clip, ready_at)
        change_kind = EventChangeKind.MEDIA_READY
        payload = {"partial_clip": job.is_partial}
    else:
        error = (job.error_message or "Kanıt hazırlama bilinmeyen nedenle başarısız")[:500]
        for record in (snapshot, clip):
            record.status = MediaStatus.FAILED
            record.error_message = error
        change_kind = EventChangeKind.MEDIA_FAILED
        payload = {"error": error}
    _add_change(database, job.event_id, change_kind, payload)
    database.flush()
    return snapshot, clip


def _source_datetime(camera_session: CameraSession, source_seconds: float) -> datetime:
    source_start = (camera_session.source_start_time_ms or 0) / 1000
    elapsed = source_seconds - source_start
    if elapsed < 0:
        raise ValueError("Olay zamanı kamera oturumunun kaynak başlangıcından önce olamaz")
    return camera_session.started_at + timedelta(seconds=elapsed)


def _validate_existing_event(
    event: SafetyEvent,
    transition: EventTransition,
    context: EventPersistenceContext,
) -> None:
    expected = (
        context.camera_id,
        transition.key.camera_session_id,
        transition.key.rule_version_id,
        transition.key.track_id,
        context.identity_status,
        context.employee_id,
        context.model_version.strip(),
    )
    actual = (
        event.camera_id,
        event.camera_session_id,
        event.rule_version_id,
        event.track_id,
        event.identity_status,
        event.employee_id,
        event.model_version,
    )
    if actual != expected:
        raise ValueError("Aynı olay kimliği farklı kamera, takip, kural veya kişiye ait")


def _add_change(
    database: Session,
    event_id: uuid.UUID,
    kind: EventChangeKind,
    payload: dict[str, object],
) -> None:
    database.add(EventChange(event_id=event_id, change_kind=kind, payload=payload))


def _mark_media_ready(record: MediaRecord, artifact, ready_at: datetime) -> None:
    record.status = MediaStatus.READY
    record.relative_path = artifact.relative_path
    record.mime_type = artifact.mime_type
    record.size_bytes = artifact.size_bytes
    record.sha256 = artifact.sha256
    record.ready_at = ready_at
    record.error_message = None
