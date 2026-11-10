"""Tek karelik kural sonucunu süreli ve tekrarlı olay adayına dönüştürür.

Bu modül olay satırı yazmaz. E1 yalnız bir adayın yeterli zamansal kanıta ulaşıp
ulaşmadığını belirler; olay birleştirme ve bitiş yaşam döngüsü E2'nin işidir.
"""

from __future__ import annotations

import math
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum

from isg_api.rules import Assessment, Equipment


class TemporalDecision(StrEnum):
    CLEAR = "clear"
    ACCUMULATING = "accumulating"
    CANDIDATE = "candidate"
    UNASSESSABLE = "unassessable"


@dataclass(frozen=True, slots=True)
class TemporalPolicy:
    """5–10 analiz karesi/saniye hedefi için ölçülecek başlangıç eşikleri."""

    minimum_violation_observations: int = 4
    minimum_violation_duration_seconds: float = 1.5
    observation_window_seconds: float = 3.0
    maximum_violation_gap_seconds: float = 1.0
    stale_state_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.minimum_violation_observations < 2:
            raise ValueError("En az iki ihlal-adayı gözlem gerekli olmalıdır")
        numeric_values = (
            self.minimum_violation_duration_seconds,
            self.observation_window_seconds,
            self.maximum_violation_gap_seconds,
            self.stale_state_seconds,
        )
        if any(not math.isfinite(value) or value <= 0 for value in numeric_values):
            raise ValueError("Zamansal eşikler sonlu ve sıfırdan büyük olmalıdır")
        if self.minimum_violation_duration_seconds > self.observation_window_seconds:
            raise ValueError("Asgari süre gözlem penceresinden uzun olamaz")
        if self.maximum_violation_gap_seconds > self.observation_window_seconds:
            raise ValueError("Azami boşluk gözlem penceresinden uzun olamaz")
        if self.stale_state_seconds <= self.maximum_violation_gap_seconds:
            raise ValueError("Eski durum süresi azami gözlem boşluğundan uzun olmalıdır")


@dataclass(frozen=True, slots=True)
class TemporalObservationKey:
    camera_session_id: uuid.UUID
    rule_version_id: uuid.UUID
    track_id: int
    equipment: Equipment

    def __post_init__(self) -> None:
        if self.track_id < 0:
            raise ValueError("Takip numarası negatif olamaz")


@dataclass(frozen=True, slots=True)
class TemporalResult:
    key: TemporalObservationKey
    decision: TemporalDecision
    candidate_ready: bool
    became_candidate: bool
    violation_observation_count: int
    violation_duration_seconds: float


@dataclass(slots=True)
class _CandidateState:
    violation_times: deque[float] = field(default_factory=deque)
    last_input_at: float | None = None
    last_violation_at: float | None = None
    confirmed: bool = False

    def clear_evidence(self) -> None:
        self.violation_times.clear()
        self.last_violation_at = None
        self.confirmed = False


class TemporalViolationTracker:
    """Oturum + takip + kural sürümü + ekipman başına bağımsız kanıt tutar."""

    def __init__(self, policy: TemporalPolicy | None = None) -> None:
        self.policy = policy or TemporalPolicy()
        self._states: dict[TemporalObservationKey, _CandidateState] = {}

    def observe(
        self,
        key: TemporalObservationKey,
        assessment: Assessment,
        observed_at_seconds: float,
    ) -> TemporalResult:
        if not math.isfinite(observed_at_seconds) or observed_at_seconds < 0:
            raise ValueError("Gözlem zamanı sonlu ve negatif olmayan saniye olmalıdır")

        state = self._states.setdefault(key, _CandidateState())
        if state.last_input_at is not None and observed_at_seconds < state.last_input_at:
            raise ValueError("Aynı takip anahtarındaki gözlem zamanı geriye gidemez")
        state.last_input_at = observed_at_seconds

        if assessment is Assessment.COMPLIANT:
            state.clear_evidence()
            return self._result(key, state, TemporalDecision.CLEAR, became_candidate=False)

        if assessment is Assessment.UNASSESSABLE:
            if (
                state.last_violation_at is not None
                and observed_at_seconds - state.last_violation_at
                > self.policy.maximum_violation_gap_seconds
            ):
                state.clear_evidence()
            self._drop_outside_window(state, observed_at_seconds)
            return self._result(
                key,
                state,
                TemporalDecision.UNASSESSABLE,
                became_candidate=False,
            )

        if assessment is not Assessment.VIOLATION_CANDIDATE:
            raise ValueError(f"Desteklenmeyen değerlendirme: {assessment}")

        if (
            state.last_violation_at is not None
            and observed_at_seconds - state.last_violation_at
            > self.policy.maximum_violation_gap_seconds
        ):
            state.clear_evidence()
        self._drop_outside_window(state, observed_at_seconds)
        state.violation_times.append(observed_at_seconds)
        state.last_violation_at = observed_at_seconds

        duration = self._duration(state)
        enough_evidence = (
            len(state.violation_times) >= self.policy.minimum_violation_observations
            and duration >= self.policy.minimum_violation_duration_seconds
        )
        became_candidate = enough_evidence and not state.confirmed
        if enough_evidence:
            state.confirmed = True
        decision = TemporalDecision.CANDIDATE if state.confirmed else TemporalDecision.ACCUMULATING
        return self._result(key, state, decision, became_candidate=became_candidate)

    def prune_stale(self, current_time_seconds: float) -> int:
        """Uzun süredir gözlenmeyen takip belleğini sınırsız büyümeden temizler."""
        if not math.isfinite(current_time_seconds) or current_time_seconds < 0:
            raise ValueError("Temizleme zamanı sonlu ve negatif olmayan saniye olmalıdır")
        stale_keys = [
            key
            for key, state in self._states.items()
            if state.last_input_at is not None
            and current_time_seconds - state.last_input_at > self.policy.stale_state_seconds
        ]
        for key in stale_keys:
            del self._states[key]
        return len(stale_keys)

    def reset_session(self, camera_session_id: uuid.UUID) -> int:
        """Yeni oynatma/kamera oturumunda eski takip kanıtını yeniden kullanmaz."""
        session_keys = [key for key in self._states if key.camera_session_id == camera_session_id]
        for key in session_keys:
            del self._states[key]
        return len(session_keys)

    def _drop_outside_window(self, state: _CandidateState, observed_at_seconds: float) -> None:
        while (
            state.violation_times
            and observed_at_seconds - state.violation_times[0]
            > self.policy.observation_window_seconds
        ):
            state.violation_times.popleft()
        if not state.violation_times:
            state.confirmed = False
            state.last_violation_at = None

    @staticmethod
    def _duration(state: _CandidateState) -> float:
        if len(state.violation_times) < 2:
            return 0.0
        return state.violation_times[-1] - state.violation_times[0]

    def _result(
        self,
        key: TemporalObservationKey,
        state: _CandidateState,
        decision: TemporalDecision,
        *,
        became_candidate: bool,
    ) -> TemporalResult:
        return TemporalResult(
            key=key,
            decision=decision,
            candidate_ready=state.confirmed,
            became_candidate=became_candidate,
            violation_observation_count=len(state.violation_times),
            violation_duration_seconds=round(self._duration(state), 6),
        )
