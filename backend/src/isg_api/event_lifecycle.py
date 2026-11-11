"""Süreli ihlal adaylarını tekil teknik olay yaşam döngüsüne dönüştürür.

E2 veritabanına yazmaz ve bildirim göndermez. Her geçiş, E4'te kalıcı kayıt ve
bildirim katmanının kullanacağı açık bir komut üretir.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum

from isg_api.models import TechnicalStatus
from isg_api.rules import Equipment


class EventTransitionKind(StrEnum):
    STARTED = "started"
    UPDATED = "updated"
    ENDED = "ended"


class EventEndReason(StrEnum):
    RESOLVED = "resolved"
    OBSERVATION_LOST = "observation_lost"
    SESSION_ENDED = "session_ended"
    RULE_CHANGED = "rule_changed"


@dataclass(frozen=True, slots=True)
class EventLifecyclePolicy:
    resolution_observations: int = 2
    resolution_duration_seconds: float = 1.0
    observation_lost_seconds: float = 2.0

    def __post_init__(self) -> None:
        if self.resolution_observations < 2:
            raise ValueError("Olayı bitirmek için en az iki uygun gözlem gerekir")
        values = (self.resolution_duration_seconds, self.observation_lost_seconds)
        if any(not math.isfinite(value) or value <= 0 for value in values):
            raise ValueError("Olay yaşam döngüsü süreleri sonlu ve pozitif olmalıdır")
        if self.observation_lost_seconds <= self.resolution_duration_seconds:
            raise ValueError("Gözlem kaybı süresi düzelme süresinden uzun olmalıdır")


@dataclass(frozen=True, slots=True)
class EventLifecycleKey:
    camera_session_id: uuid.UUID
    rule_version_id: uuid.UUID
    track_id: int

    def __post_init__(self) -> None:
        if self.track_id < 0:
            raise ValueError("Takip numarası negatif olamaz")


@dataclass(frozen=True, slots=True)
class EventTransition:
    event_id: uuid.UUID
    key: EventLifecycleKey
    kind: EventTransitionKind
    technical_status: TechnicalStatus
    notification_required: bool
    observed_equipment: tuple[Equipment, ...]
    current_equipment: tuple[Equipment, ...]
    started_at_seconds: float
    last_seen_at_seconds: float
    ended_at_seconds: float | None = None
    end_reason: EventEndReason | None = None


@dataclass(slots=True)
class _ActiveEvent:
    event_id: uuid.UUID
    key: EventLifecycleKey
    started_at: float
    last_seen_at: float
    last_violation_at: float
    observed_equipment: set[Equipment] = field(default_factory=set)
    current_equipment: set[Equipment] = field(default_factory=set)
    clear_started_at: float | None = None
    clear_observations: int = 0


TrackKey = tuple[uuid.UUID, int]


class EventLifecycleTracker:
    """Kamera oturumundaki her takip için en fazla bir açık olay tutar."""

    def __init__(
        self,
        policy: EventLifecyclePolicy | None = None,
        *,
        event_id_factory: Callable[[], uuid.UUID] = uuid.uuid4,
    ) -> None:
        self.policy = policy or EventLifecyclePolicy()
        self._event_id_factory = event_id_factory
        self._active: dict[TrackKey, _ActiveEvent] = {}
        self._last_input_at: dict[TrackKey, float] = {}

    @property
    def active_event_count(self) -> int:
        return len(self._active)

    def observe(
        self,
        key: EventLifecycleKey,
        candidate_equipment: Iterable[Equipment],
        observed_at_seconds: float,
    ) -> tuple[EventTransition, ...]:
        self._validate_time(observed_at_seconds)
        track_key = (key.camera_session_id, key.track_id)
        previous_time = self._last_input_at.get(track_key)
        if previous_time is not None and observed_at_seconds < previous_time:
            raise ValueError("Aynı takipte olay zamanı geriye gidemez")
        self._last_input_at[track_key] = observed_at_seconds

        equipment = set(candidate_equipment)
        active = self._active.get(track_key)
        transitions: list[EventTransition] = []

        if active is not None and active.key.rule_version_id != key.rule_version_id:
            transitions.append(
                self._end(track_key, observed_at_seconds, EventEndReason.RULE_CHANGED)
            )
            active = None

        if equipment:
            if active is None:
                active = _ActiveEvent(
                    event_id=self._event_id_factory(),
                    key=key,
                    started_at=observed_at_seconds,
                    last_seen_at=observed_at_seconds,
                    last_violation_at=observed_at_seconds,
                    observed_equipment=set(equipment),
                    current_equipment=set(equipment),
                )
                self._active[track_key] = active
                transitions.append(
                    self._transition(
                        active,
                        EventTransitionKind.STARTED,
                        notification_required=True,
                    )
                )
                return tuple(transitions)

            active.last_seen_at = observed_at_seconds
            active.last_violation_at = observed_at_seconds
            active.observed_equipment.update(equipment)
            active.current_equipment = equipment
            active.clear_started_at = None
            active.clear_observations = 0
            transitions.append(
                self._transition(
                    active,
                    EventTransitionKind.UPDATED,
                    notification_required=False,
                )
            )
            return tuple(transitions)

        if active is None:
            return tuple(transitions)

        active.last_seen_at = observed_at_seconds
        active.current_equipment.clear()
        if active.clear_started_at is None:
            active.clear_started_at = observed_at_seconds
            active.clear_observations = 1
        else:
            active.clear_observations += 1

        resolution_duration = observed_at_seconds - active.clear_started_at
        if (
            active.clear_observations >= self.policy.resolution_observations
            and resolution_duration >= self.policy.resolution_duration_seconds
        ):
            transitions.append(self._end(track_key, observed_at_seconds, EventEndReason.RESOLVED))
        else:
            transitions.append(
                self._transition(
                    active,
                    EventTransitionKind.UPDATED,
                    notification_required=False,
                )
            )
        return tuple(transitions)

    def expire_missing(self, current_time_seconds: float) -> tuple[EventTransition, ...]:
        """Yeni karede görülmeyen takipleri belirli süre sonra açık nedenle kapatır."""
        self._validate_time(current_time_seconds)
        expired = [
            track_key
            for track_key, active in self._active.items()
            if current_time_seconds - active.last_seen_at >= self.policy.observation_lost_seconds
        ]
        return tuple(
            self._end(track_key, current_time_seconds, EventEndReason.OBSERVATION_LOST)
            for track_key in expired
        )

    def end_session(
        self, camera_session_id: uuid.UUID, ended_at_seconds: float
    ) -> tuple[EventTransition, ...]:
        self._validate_time(ended_at_seconds)
        session_keys = [
            track_key for track_key in self._active if track_key[0] == camera_session_id
        ]
        for track_key in session_keys:
            active = self._active[track_key]
            if ended_at_seconds < active.last_seen_at:
                raise ValueError("Oturum bitiş zamanı son olay gözleminden önce olamaz")
        transitions = tuple(
            self._end(track_key, ended_at_seconds, EventEndReason.SESSION_ENDED)
            for track_key in session_keys
        )
        self._last_input_at = {
            track_key: value
            for track_key, value in self._last_input_at.items()
            if track_key[0] != camera_session_id
        }
        return transitions

    @staticmethod
    def _validate_time(value: float) -> None:
        if not math.isfinite(value) or value < 0:
            raise ValueError("Olay zamanı sonlu ve negatif olmayan saniye olmalıdır")

    def _end(
        self,
        track_key: TrackKey,
        ended_at_seconds: float,
        reason: EventEndReason,
    ) -> EventTransition:
        active = self._active.pop(track_key)
        active.current_equipment.clear()
        return self._transition(
            active,
            EventTransitionKind.ENDED,
            notification_required=False,
            ended_at_seconds=ended_at_seconds,
            end_reason=reason,
        )

    @staticmethod
    def _transition(
        active: _ActiveEvent,
        kind: EventTransitionKind,
        *,
        notification_required: bool,
        ended_at_seconds: float | None = None,
        end_reason: EventEndReason | None = None,
    ) -> EventTransition:
        return EventTransition(
            event_id=active.event_id,
            key=active.key,
            kind=kind,
            technical_status=(
                TechnicalStatus.ENDED
                if kind is EventTransitionKind.ENDED
                else TechnicalStatus.ACTIVE
            ),
            notification_required=notification_required,
            observed_equipment=tuple(sorted(active.observed_equipment)),
            current_equipment=tuple(sorted(active.current_equipment)),
            started_at_seconds=active.started_at,
            last_seen_at_seconds=active.last_seen_at,
            ended_at_seconds=ended_at_seconds,
            end_reason=end_reason,
        )
