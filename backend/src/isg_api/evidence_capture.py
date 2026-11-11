"""Olay fotoğrafı ve kısa klip için sınırlı, asenkron kanıt tamponu.

Analiz süreci JPEG olarak sıkıştırılmış kareleri bu bileşene verir. Bileşen RAM'i
süre, kare sayısı ve bayt sınırıyla korur; dosya yazımını ayrı bir iş parçacığına
aktarır. Böylece yavaş disk veya video kodlama canlı analizi bekletmez.
"""

from __future__ import annotations

import hashlib
import math
import os
import queue
import threading
import uuid
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class EvidenceStatus(StrEnum):
    PREPARING = "preparing"
    READY = "ready"
    FAILED = "failed"


class EvidenceCompletionReason(StrEnum):
    POST_WINDOW_COMPLETE = "post_window_complete"
    SESSION_ENDED = "session_ended"


@dataclass(frozen=True, slots=True)
class EvidencePolicy:
    pre_event_seconds: float = 5.0
    post_event_seconds: float = 5.0
    max_buffer_frames: int = 150
    max_buffer_bytes: int = 32 * 1024 * 1024
    max_pending_writes: int = 8

    def __post_init__(self) -> None:
        durations = (self.pre_event_seconds, self.post_event_seconds)
        if any(not math.isfinite(value) or value < 0 for value in durations):
            raise ValueError("Kanıt tamponu süreleri sonlu ve negatif olmayan değerler olmalıdır")
        if self.pre_event_seconds == 0 and self.post_event_seconds == 0:
            raise ValueError("Kanıt penceresinin en az bir tarafı sıfırdan büyük olmalıdır")
        if self.max_buffer_frames <= 0:
            raise ValueError("Kanıt tamponu kare sınırı pozitif olmalıdır")
        if self.max_buffer_bytes <= 0:
            raise ValueError("Kanıt tamponu bayt sınırı pozitif olmalıdır")
        if self.max_pending_writes <= 0:
            raise ValueError("Bekleyen medya işi sınırı pozitif olmalıdır")


@dataclass(frozen=True, slots=True)
class EncodedEvidenceFrame:
    session_id: str
    source_timestamp_seconds: float
    observed_at_utc: datetime
    jpeg_bytes: bytes
    width: int
    height: int

    def __post_init__(self) -> None:
        if not self.session_id.strip():
            raise ValueError("Kare oturum kimliği boş olamaz")
        if not math.isfinite(self.source_timestamp_seconds) or self.source_timestamp_seconds < 0:
            raise ValueError("Kare kaynak zamanı sonlu ve negatif olmayan bir değer olmalıdır")
        if self.observed_at_utc.tzinfo is None or self.observed_at_utc.utcoffset() is None:
            raise ValueError("Kare gözlem zamanı saat dilimi içermelidir")
        if not self.jpeg_bytes:
            raise ValueError("Sıkıştırılmış kare boş olamaz")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Kare boyutları pozitif olmalıdır")

    @property
    def size_bytes(self) -> int:
        return len(self.jpeg_bytes)


@dataclass(frozen=True, slots=True)
class EvidenceArtifact:
    relative_path: str
    mime_type: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class EvidenceWriteResult:
    snapshot: EvidenceArtifact
    clip: EvidenceArtifact


@dataclass(frozen=True, slots=True)
class PreparedEvidence:
    event_id: uuid.UUID
    session_id: str
    snapshot_frame: EncodedEvidenceFrame
    clip_frames: tuple[EncodedEvidenceFrame, ...]
    completion_reason: EvidenceCompletionReason
    is_partial: bool


@dataclass(frozen=True, slots=True)
class EvidenceJobSnapshot:
    event_id: uuid.UUID
    session_id: str
    status: EvidenceStatus
    snapshot_source_time: float
    clip_frame_count: int
    clip_start_source_time: float
    clip_end_source_time: float
    completion_reason: EvidenceCompletionReason | None
    is_partial: bool
    result: EvidenceWriteResult | None
    error_message: str | None


class EvidenceWriter(Protocol):
    def write(self, evidence: PreparedEvidence) -> EvidenceWriteResult: ...


class ClipEncoder(Protocol):
    def encode(self, path: Path, frames: Sequence[EncodedEvidenceFrame]) -> None: ...


class OpenCvMp4Encoder:
    """JPEG kareleri tarayıcıların açabildiği kısa MP4 dosyasına dönüştürür."""

    def encode(self, path: Path, frames: Sequence[EncodedEvidenceFrame]) -> None:
        # Medya özelliği kullanılmadığında sunucu OpenCV'yi yüklemek zorunda kalmaz.
        import cv2
        import numpy as np

        if not frames:
            raise ValueError("Klip için en az bir kare gerekir")
        width, height = frames[0].width, frames[0].height
        fps = _estimate_fps(frames)
        writer = cv2.VideoWriter(
            str(path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )
        if not writer.isOpened():
            writer.release()
            raise RuntimeError("MP4 kodlayıcı açılamadı")
        try:
            for frame in frames:
                image = cv2.imdecode(
                    np.frombuffer(frame.jpeg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR
                )
                if image is None:
                    raise ValueError("Klipte çözülemeyen JPEG kare var")
                if image.shape[1] != width or image.shape[0] != height:
                    image = cv2.resize(image, (width, height))
                writer.write(image)
        finally:
            writer.release()


class FilesystemEvidenceWriter:
    """Fotoğrafı ve klibi geçici dosya üzerinden atomik olarak medya köküne yazar."""

    def __init__(self, media_root: Path, *, clip_encoder: ClipEncoder | None = None) -> None:
        self.media_root = media_root.resolve()
        self._clip_encoder = clip_encoder or OpenCvMp4Encoder()

    def write(self, evidence: PreparedEvidence) -> EvidenceWriteResult:
        event_directory = self.media_root / "events" / str(evidence.event_id)
        event_directory.mkdir(parents=True, exist_ok=True)
        snapshot_path = event_directory / "snapshot.jpg"
        clip_path = event_directory / "clip.mp4"
        snapshot_temp = event_directory / "snapshot.part.jpg"
        clip_temp = event_directory / "clip.part.mp4"

        if snapshot_path.exists() or clip_path.exists():
            raise FileExistsError("Bu olayın kanıt dosyası zaten var; üzerine yazılmadı")

        for path in (snapshot_temp, clip_temp):
            path.unlink(missing_ok=True)
        try:
            snapshot_temp.write_bytes(evidence.snapshot_frame.jpeg_bytes)
            self._clip_encoder.encode(clip_temp, evidence.clip_frames)
            if not clip_temp.is_file() or clip_temp.stat().st_size == 0:
                raise RuntimeError("Klip kodlayıcı boş dosya üretti")
            os.replace(clip_temp, clip_path)
            os.replace(snapshot_temp, snapshot_path)
        except Exception:
            snapshot_temp.unlink(missing_ok=True)
            clip_temp.unlink(missing_ok=True)
            snapshot_path.unlink(missing_ok=True)
            clip_path.unlink(missing_ok=True)
            raise

        return EvidenceWriteResult(
            snapshot=_artifact(self.media_root, snapshot_path, "image/jpeg"),
            clip=_artifact(self.media_root, clip_path, "video/mp4"),
        )


@dataclass(slots=True)
class _ActiveCapture:
    event_id: uuid.UUID
    session_id: str
    event_time: float
    deadline: float
    snapshot_frame: EncodedEvidenceFrame
    frames: list[EncodedEvidenceFrame]


@dataclass(slots=True)
class _EvidenceJob:
    event_id: uuid.UUID
    session_id: str
    snapshot_source_time: float
    clip_frame_count: int
    clip_start_source_time: float
    clip_end_source_time: float
    status: EvidenceStatus = EvidenceStatus.PREPARING
    completion_reason: EvidenceCompletionReason | None = None
    is_partial: bool = False
    result: EvidenceWriteResult | None = None
    error_message: str | None = None


class EvidenceCaptureManager:
    """Kareleri sınırlar ve tamamlanan kanıt işlerini beklemeden yazma kuyruğuna atar."""

    _STOP = object()

    def __init__(
        self,
        writer: EvidenceWriter,
        policy: EvidencePolicy | None = None,
        *,
        thread_factory: Callable[..., threading.Thread] = threading.Thread,
    ) -> None:
        self.policy = policy or EvidencePolicy()
        self._writer = writer
        self._frames: deque[EncodedEvidenceFrame] = deque()
        self._buffer_bytes = 0
        self._session_id: str | None = None
        self._last_source_time: float | None = None
        self._active: dict[uuid.UUID, _ActiveCapture] = {}
        self._jobs: dict[uuid.UUID, _EvidenceJob] = {}
        self._done_events: dict[uuid.UUID, threading.Event] = {}
        self._lock = threading.Lock()
        self._write_queue: queue.Queue[PreparedEvidence | object] = queue.Queue(
            maxsize=self.policy.max_pending_writes
        )
        self._closed = False
        self._worker = thread_factory(
            target=self._worker_loop,
            name="isg-evidence-writer",
            daemon=True,
        )
        self._worker.start()

    @property
    def buffered_frame_count(self) -> int:
        with self._lock:
            return len(self._frames)

    @property
    def buffered_bytes(self) -> int:
        with self._lock:
            return self._buffer_bytes

    def start_session(self, session_id: str) -> None:
        session_id = session_id.strip()
        if not session_id:
            raise ValueError("Kanıt oturumu kimliği boş olamaz")
        with self._lock:
            self._ensure_open()
            if self._session_id is not None and self._session_id != session_id:
                raise RuntimeError("Önce etkin kanıt oturumu bitirilmelidir")
            if self._session_id == session_id:
                return
            self._session_id = session_id
            self._last_source_time = None
            self._clear_buffer()

    def ingest(self, frame: EncodedEvidenceFrame) -> tuple[uuid.UUID, ...]:
        """Kareyi ve etkin klipleri günceller; dosya yazılmasını hiçbir zaman beklemez."""
        with self._lock:
            self._ensure_open()
            if frame.session_id != self._session_id:
                raise RuntimeError("Kare etkin kanıt oturumuna ait değil")
            if self._last_source_time is not None and (
                frame.source_timestamp_seconds < self._last_source_time
            ):
                raise ValueError("Kanıt karelerinin kaynak zamanı geriye gidemez")
            self._last_source_time = frame.source_timestamp_seconds
            self._append_buffer(frame)

            completed: list[uuid.UUID] = []
            for capture in tuple(self._active.values()):
                if frame.source_timestamp_seconds > capture.event_time:
                    capture.frames.append(frame)
                if frame.source_timestamp_seconds >= capture.deadline:
                    self._submit(capture, EvidenceCompletionReason.POST_WINDOW_COMPLETE, False)
                    completed.append(capture.event_id)
            return tuple(completed)

    def start_event(
        self,
        event_id: uuid.UUID,
        *,
        session_id: str,
        event_source_time: float,
    ) -> EvidenceJobSnapshot:
        with self._lock:
            self._ensure_open()
            if event_id in self._jobs:
                raise ValueError("Bu olay için kanıt işi zaten oluşturuldu")
            if session_id != self._session_id:
                raise RuntimeError("Olay etkin kanıt oturumuna ait değil")
            if not math.isfinite(event_source_time) or event_source_time < 0:
                raise ValueError("Olay kaynak zamanı sonlu ve negatif olmayan bir değer olmalıdır")
            eligible = [
                frame
                for frame in self._frames
                if event_source_time - self.policy.pre_event_seconds
                <= frame.source_timestamp_seconds
                <= event_source_time
            ]
            if not eligible:
                raise RuntimeError("Olay fotoğrafı için uygun tampon karesi yok")
            snapshot_frame = min(
                eligible,
                key=lambda frame: abs(frame.source_timestamp_seconds - event_source_time),
            )
            capture = _ActiveCapture(
                event_id=event_id,
                session_id=session_id,
                event_time=event_source_time,
                deadline=event_source_time + self.policy.post_event_seconds,
                snapshot_frame=snapshot_frame,
                frames=list(eligible),
            )
            job = _EvidenceJob(
                event_id=event_id,
                session_id=session_id,
                snapshot_source_time=snapshot_frame.source_timestamp_seconds,
                clip_frame_count=len(capture.frames),
                clip_start_source_time=capture.frames[0].source_timestamp_seconds,
                clip_end_source_time=capture.frames[-1].source_timestamp_seconds,
            )
            self._active[event_id] = capture
            self._jobs[event_id] = job
            self._done_events[event_id] = threading.Event()
            if self.policy.post_event_seconds == 0:
                self._submit(capture, EvidenceCompletionReason.POST_WINDOW_COMPLETE, False)
            return self._snapshot(job)

    def end_session(self, session_id: str) -> tuple[uuid.UUID, ...]:
        """Kamera/video bittiğinde açık klipleri kısa ama kullanılabilir kanıt olarak yollar."""
        with self._lock:
            self._ensure_open()
            if session_id != self._session_id:
                raise RuntimeError("Biten oturum etkin kanıt oturumu değil")
            submitted = tuple(self._active)
            for capture in tuple(self._active.values()):
                self._submit(capture, EvidenceCompletionReason.SESSION_ENDED, True)
            self._session_id = None
            self._last_source_time = None
            self._clear_buffer()
            return submitted

    def job_snapshot(self, event_id: uuid.UUID) -> EvidenceJobSnapshot:
        with self._lock:
            job = self._jobs.get(event_id)
            if job is None:
                raise KeyError(event_id)
            return self._snapshot(job)

    def wait_until_finished(self, event_id: uuid.UUID, timeout: float = 5.0) -> EvidenceJobSnapshot:
        """Yalnız test/kapanış gibi kontrol akışları içindir; analiz döngüsünde kullanılmaz."""
        with self._lock:
            done = self._done_events.get(event_id)
            if done is None:
                raise KeyError(event_id)
        if not done.wait(timeout):
            raise TimeoutError("Kanıt yazma işi verilen sürede tamamlanmadı")
        return self.job_snapshot(event_id)

    def close(self, timeout: float = 5.0) -> None:
        """İşçi thread'ini kontrollü kapatır; uygulama kapanışında çağrılmalıdır."""
        with self._lock:
            if self._closed:
                return
            if self._session_id is not None:
                for capture in tuple(self._active.values()):
                    self._submit(capture, EvidenceCompletionReason.SESSION_ENDED, True)
                self._session_id = None
                self._clear_buffer()
            self._closed = True
        try:
            self._write_queue.put_nowait(self._STOP)
        except queue.Full:
            # Kuyruk doluysa işçi bir işi alınca kapanış işaretini güvenle ekleyebiliriz.
            self._write_queue.put(self._STOP, timeout=timeout)
        self._worker.join(timeout)
        if self._worker.is_alive():
            raise TimeoutError("Kanıt yazma işçisi verilen sürede kapanmadı")

    def _append_buffer(self, frame: EncodedEvidenceFrame) -> None:
        self._frames.append(frame)
        self._buffer_bytes += frame.size_bytes
        oldest_allowed = frame.source_timestamp_seconds - self.policy.pre_event_seconds
        while self._frames and (
            self._frames[0].source_timestamp_seconds < oldest_allowed
            or len(self._frames) > self.policy.max_buffer_frames
            or self._buffer_bytes > self.policy.max_buffer_bytes
        ):
            removed = self._frames.popleft()
            self._buffer_bytes -= removed.size_bytes

    def _clear_buffer(self) -> None:
        self._frames.clear()
        self._buffer_bytes = 0

    def _submit(
        self,
        capture: _ActiveCapture,
        reason: EvidenceCompletionReason,
        is_partial: bool,
    ) -> None:
        self._active.pop(capture.event_id, None)
        evidence = PreparedEvidence(
            event_id=capture.event_id,
            session_id=capture.session_id,
            snapshot_frame=capture.snapshot_frame,
            clip_frames=tuple(capture.frames),
            completion_reason=reason,
            is_partial=is_partial,
        )
        job = self._jobs[capture.event_id]
        job.clip_frame_count = len(capture.frames)
        job.clip_start_source_time = capture.frames[0].source_timestamp_seconds
        job.clip_end_source_time = capture.frames[-1].source_timestamp_seconds
        job.completion_reason = reason
        job.is_partial = is_partial
        try:
            self._write_queue.put_nowait(evidence)
        except queue.Full:
            job.status = EvidenceStatus.FAILED
            job.error_message = "Medya yazma kuyruğu dolu; analiz akışı bekletilmedi"
            self._done_events[capture.event_id].set()

    def _worker_loop(self) -> None:
        while True:
            evidence = self._write_queue.get()
            try:
                if evidence is self._STOP:
                    return
                assert isinstance(evidence, PreparedEvidence)
                try:
                    result = self._writer.write(evidence)
                except Exception as error:
                    with self._lock:
                        job = self._jobs[evidence.event_id]
                        job.status = EvidenceStatus.FAILED
                        job.error_message = _safe_error(error)
                        self._done_events[evidence.event_id].set()
                else:
                    with self._lock:
                        job = self._jobs[evidence.event_id]
                        job.status = EvidenceStatus.READY
                        job.result = result
                        self._done_events[evidence.event_id].set()
            finally:
                self._write_queue.task_done()

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("Kanıt yöneticisi kapalı")

    @staticmethod
    def _snapshot(job: _EvidenceJob) -> EvidenceJobSnapshot:
        return EvidenceJobSnapshot(
            event_id=job.event_id,
            session_id=job.session_id,
            status=job.status,
            snapshot_source_time=job.snapshot_source_time,
            clip_frame_count=job.clip_frame_count,
            clip_start_source_time=job.clip_start_source_time,
            clip_end_source_time=job.clip_end_source_time,
            completion_reason=job.completion_reason,
            is_partial=job.is_partial,
            result=job.result,
            error_message=job.error_message,
        )


def _estimate_fps(frames: Sequence[EncodedEvidenceFrame]) -> float:
    intervals = [
        later.source_timestamp_seconds - earlier.source_timestamp_seconds
        for earlier, later in zip(frames, frames[1:], strict=False)
        if later.source_timestamp_seconds > earlier.source_timestamp_seconds
    ]
    if not intervals:
        return 1.0
    intervals.sort()
    median = intervals[len(intervals) // 2]
    return min(30.0, max(1.0, 1.0 / median))


def _artifact(root: Path, path: Path, mime_type: str) -> EvidenceArtifact:
    content = path.read_bytes()
    relative_path = path.relative_to(root).as_posix()
    return EvidenceArtifact(
        relative_path=relative_path,
        mime_type=mime_type,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )


def _safe_error(error: Exception) -> str:
    message = " ".join(str(error).split()) or "ayrıntı yok"
    return f"{type(error).__name__}: {message}"[:500]


def utc_now() -> datetime:
    return datetime.now(UTC)
