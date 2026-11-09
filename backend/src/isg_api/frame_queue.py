"""Canlı analiz için eski kareleri biriktirmeyen sınırlı ve izlenebilir kuyruk."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from threading import Condition

from isg_api.video_source import VideoFrame


class FramePipelineStatus(StrEnum):
    IDLE = "idle"
    HEALTHY = "healthy"
    BACKLOG = "backlog"
    STALE = "stale"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class FrameQueueSnapshot:
    session_id: str | None
    status: FramePipelineStatus
    queue_size: int
    capacity: int
    received_count: int
    processed_count: int
    dropped_count: int
    last_received_at_utc: datetime | None
    last_processed_at_utc: datetime | None
    frame_age_seconds: float | None
    last_processing_latency_ms: float | None


class LatestFrameQueue:
    """Kuyruk dolduğunda en eski kareyi atarak canlılığı gecikmeye tercih eder."""

    def __init__(
        self,
        capacity: int = 2,
        *,
        stale_after_seconds: float = 2.0,
        monotonic=time.monotonic,
        utc_now=lambda: datetime.now(UTC),
    ) -> None:
        if capacity <= 0:
            raise ValueError("Kare kuyruğu kapasitesi pozitif olmalıdır")
        if stale_after_seconds <= 0:
            raise ValueError("Donma eşiği pozitif olmalıdır")
        self.capacity = capacity
        self.stale_after_seconds = stale_after_seconds
        self._monotonic = monotonic
        self._utc_now = utc_now
        self._condition = Condition()
        self._frames: deque[VideoFrame] = deque()
        self._session_id: str | None = None
        self._closed = True
        self._received_count = 0
        self._processed_count = 0
        self._dropped_count = 0
        self._last_received_monotonic: float | None = None
        self._last_received_at_utc: datetime | None = None
        self._last_processed_at_utc: datetime | None = None
        self._last_processing_latency_ms: float | None = None

    def start_session(self, session_id: str) -> None:
        """Yeni kamera oturumunda eski kare ve sayaçları tamamen sıfırlar."""
        if not session_id:
            raise ValueError("Oturum kimliği boş olamaz")
        with self._condition:
            self._frames.clear()
            self._session_id = session_id
            self._closed = False
            self._received_count = 0
            self._processed_count = 0
            self._dropped_count = 0
            self._last_received_monotonic = None
            self._last_received_at_utc = None
            self._last_processed_at_utc = None
            self._last_processing_latency_ms = None
            self._condition.notify_all()

    def put(self, frame: VideoFrame) -> None:
        """Kareyi beklemeden ekler; doluysa en eski kareyi düşürür."""
        with self._condition:
            if self._closed or self._session_id is None:
                raise RuntimeError("Kare kuyruğu için etkin oturum yok")
            if frame.session_id != self._session_id:
                raise RuntimeError("Kare etkin kuyruk oturumuna ait değil")
            if len(self._frames) >= self.capacity:
                self._frames.popleft()
                self._dropped_count += 1
            self._frames.append(frame)
            self._received_count += 1
            self._last_received_monotonic = self._monotonic()
            self._last_received_at_utc = self._utc_now()
            self._condition.notify()

    def get(self, timeout: float | None = None) -> VideoFrame | None:
        """Sıradaki kareyi bekler; kapalı ve boş kuyrukta None döndürür."""
        if timeout is not None and timeout < 0:
            raise ValueError("Bekleme süresi negatif olamaz")
        deadline = None if timeout is None else self._monotonic() + timeout
        with self._condition:
            while not self._frames:
                if self._closed:
                    return None
                remaining = None if deadline is None else deadline - self._monotonic()
                if remaining is not None and remaining <= 0:
                    raise TimeoutError("Kare bekleme süresi doldu")
                self._condition.wait(remaining)
            return self._frames.popleft()

    def mark_processed(self, frame: VideoFrame) -> None:
        """Analizi biten karenin gecikmesini ve işlenen kare sayısını kaydeder."""
        with self._condition:
            if frame.session_id != self._session_id:
                raise RuntimeError("İşlenen kare etkin kuyruk oturumuna ait değil")
            finished_at = self._utc_now()
            latency = max(0.0, (finished_at - frame.observed_at_utc).total_seconds())
            self._processed_count += 1
            self._last_processed_at_utc = finished_at
            self._last_processing_latency_ms = round(latency * 1000, 3)

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()

    def snapshot(self) -> FrameQueueSnapshot:
        """Kuyruk doluluğu ve son kare yaşından güncel sağlık durumunu üretir."""
        with self._condition:
            age = (
                max(0.0, self._monotonic() - self._last_received_monotonic)
                if self._last_received_monotonic is not None
                else None
            )
            if self._closed:
                status = FramePipelineStatus.STOPPED
            elif self._last_received_monotonic is None:
                status = FramePipelineStatus.IDLE
            elif age is not None and age > self.stale_after_seconds:
                status = FramePipelineStatus.STALE
            elif len(self._frames) >= self.capacity:
                status = FramePipelineStatus.BACKLOG
            else:
                status = FramePipelineStatus.HEALTHY
            return FrameQueueSnapshot(
                session_id=self._session_id,
                status=status,
                queue_size=len(self._frames),
                capacity=self.capacity,
                received_count=self._received_count,
                processed_count=self._processed_count,
                dropped_count=self._dropped_count,
                last_received_at_utc=self._last_received_at_utc,
                last_processed_at_utc=self._last_processed_at_utc,
                frame_age_seconds=round(age, 3) if age is not None else None,
                last_processing_latency_ms=self._last_processing_latency_ms,
            )
