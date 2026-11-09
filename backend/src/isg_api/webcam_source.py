"""Webcam görüntüsünü açık bağlantı durumları ve oturum kimliğiyle okur."""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from isg_api.video_source import OpenCvVideoCapture, VideoCapture, VideoFrame


class WebcamStatus(StrEnum):
    IDLE = "idle"
    OPENING = "opening"
    STREAMING = "streaming"
    STOPPED = "stopped"
    UNAVAILABLE = "unavailable"
    READ_ERROR = "read_error"


class WebcamUnavailableError(RuntimeError):
    """Webcam aygıtı açılamadığında üretilir."""


class WebcamReadError(RuntimeError):
    """Açılmış webcam bağlantısından görüntü alınamadığında üretilir."""


class OpenCvWebcamCapture(OpenCvVideoCapture):
    """Sayısal aygıt kimliğini OpenCV webcam bağlantısına dönüştürür."""

    def __init__(self, device_index: int) -> None:
        import cv2

        self._cv2 = cv2
        self._capture = cv2.VideoCapture(device_index)


@dataclass(frozen=True, slots=True)
class WebcamMetadata:
    source_id: str
    session_id: str
    device_index: int
    reported_fps: float | None
    width: int | None
    height: int | None
    started_at_utc: datetime


@dataclass(frozen=True, slots=True)
class WebcamStatusSnapshot:
    source_id: str
    device_index: int
    status: WebcamStatus
    message: str
    session_id: str | None
    frame_count: int
    last_frame_at_utc: datetime | None


StatusCallback = Callable[
    [WebcamStatus, str, str, int, datetime | None],
    None,
]


class WebcamSession:
    """Tek webcam bağlantısının karelerini ve yaşam döngüsünü yönetir."""

    def __init__(
        self,
        *,
        metadata: WebcamMetadata,
        capture: VideoCapture,
        status_callback: StatusCallback,
        monotonic: Callable[[], float],
        utc_now: Callable[[], datetime],
    ) -> None:
        self.metadata = metadata
        self._capture = capture
        self._status_callback = status_callback
        self._monotonic = monotonic
        self._utc_now = utc_now
        self._used = False
        self._released = False
        self._terminal_status: WebcamStatus | None = None
        self._frame_count = 0
        self._started_monotonic = monotonic()

    def _release(self) -> None:
        if not self._released:
            self._capture.release()
            self._released = True

    def close(self) -> None:
        """Bağlantıyı birden fazla kez çağrılabilen güvenli biçimde kapatır."""
        self._release()
        if self._terminal_status is None:
            self._terminal_status = WebcamStatus.STOPPED
            self._status_callback(
                WebcamStatus.STOPPED,
                "Webcam oturumu kapatıldı",
                self.metadata.session_id,
                self._frame_count,
                None,
            )

    def frames(self) -> Iterator[VideoFrame]:
        """Canlı kareleri verir; okuma hatasını normal kapanış gibi gizlemez."""
        if self._used:
            raise RuntimeError("Webcam oturumu tek kullanımlıktır; yeni oturum açılmalı")
        if self._released:
            raise RuntimeError("Kapatılmış webcam oturumu okunamaz")
        self._used = True

        try:
            while True:
                success, image = self._capture.read()
                if not success:
                    self._terminal_status = WebcamStatus.READ_ERROR
                    self._status_callback(
                        WebcamStatus.READ_ERROR,
                        "Webcam bağlantısından yeni kare okunamadı",
                        self.metadata.session_id,
                        self._frame_count,
                        None,
                    )
                    raise WebcamReadError("Webcam bağlantısından yeni kare okunamadı")

                observed_at = self._utc_now()
                source_elapsed = max(0.0, self._monotonic() - self._started_monotonic)
                frame = VideoFrame(
                    source_id=self.metadata.source_id,
                    session_id=self.metadata.session_id,
                    frame_index=self._frame_count,
                    source_timestamp_seconds=source_elapsed,
                    observed_at_utc=observed_at,
                    image=image,
                )
                self._frame_count += 1
                self._status_callback(
                    WebcamStatus.STREAMING,
                    "Webcam görüntüsü alınıyor",
                    self.metadata.session_id,
                    self._frame_count,
                    observed_at,
                )
                yield frame
        finally:
            self.close()

    def __enter__(self) -> WebcamSession:
        return self

    def __exit__(self, *_exc_info) -> None:
        self.close()


class WebcamSource:
    """Webcam açma, kapatma ve son bağlantı durumunu tek noktada tutar."""

    def __init__(
        self,
        device_index: int = 0,
        *,
        source_id: str = "webcam-0",
        capture_factory: Callable[[int], VideoCapture] = OpenCvWebcamCapture,
        monotonic: Callable[[], float] = time.monotonic,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        source_id = source_id.strip()
        if not source_id:
            raise ValueError("Kaynak kimliği boş olamaz")
        if device_index < 0:
            raise ValueError("Webcam aygıt numarası negatif olamaz")
        self.source_id = source_id
        self.device_index = device_index
        self._capture_factory = capture_factory
        self._monotonic = monotonic
        self._utc_now = utc_now
        self._lock = threading.Lock()
        self._active_session_id: str | None = None
        self._snapshot = WebcamStatusSnapshot(
            source_id=source_id,
            device_index=device_index,
            status=WebcamStatus.IDLE,
            message="Webcam henüz açılmadı",
            session_id=None,
            frame_count=0,
            last_frame_at_utc=None,
        )

    @property
    def status(self) -> WebcamStatusSnapshot:
        """API ve arayüzün okuyabileceği değişmez durum kopyasını döndürür."""
        with self._lock:
            return self._snapshot

    def _set_status(
        self,
        status: WebcamStatus,
        message: str,
        session_id: str,
        frame_count: int,
        last_frame_at_utc: datetime | None,
    ) -> None:
        with self._lock:
            if self._active_session_id != session_id:
                return
            self._snapshot = WebcamStatusSnapshot(
                source_id=self.source_id,
                device_index=self.device_index,
                status=status,
                message=message,
                session_id=session_id,
                frame_count=frame_count,
                last_frame_at_utc=(
                    last_frame_at_utc
                    if last_frame_at_utc is not None
                    else self._snapshot.last_frame_at_utc
                ),
            )
            if status in {
                WebcamStatus.STOPPED,
                WebcamStatus.UNAVAILABLE,
                WebcamStatus.READ_ERROR,
            }:
                self._active_session_id = None

    def _set_opening(self) -> None:
        self._snapshot = WebcamStatusSnapshot(
            source_id=self.source_id,
            device_index=self.device_index,
            status=WebcamStatus.OPENING,
            message="Webcam bağlantısı açılıyor",
            session_id=None,
            frame_count=0,
            last_frame_at_utc=None,
        )

    def _set_unavailable(self, message: str) -> None:
        self._snapshot = WebcamStatusSnapshot(
            source_id=self.source_id,
            device_index=self.device_index,
            status=WebcamStatus.UNAVAILABLE,
            message=message,
            session_id=None,
            frame_count=0,
            last_frame_at_utc=None,
        )

    def open_session(self) -> WebcamSession:
        """Webcam'i açar; başarısızlığı durum bilgisi ve istisnayla bildirir."""
        with self._lock:
            if self._active_session_id is not None:
                raise RuntimeError("Bu webcam için zaten etkin bir oturum var")
            self._set_opening()

        try:
            capture = self._capture_factory(self.device_index)
        except Exception as error:
            with self._lock:
                self._set_unavailable("Webcam bağlantısı oluşturulamadı")
            raise WebcamUnavailableError("Webcam bağlantısı oluşturulamadı") from error

        if not capture.is_opened:
            capture.release()
            with self._lock:
                self._set_unavailable("Webcam bulunamadı, kullanımda veya erişilemiyor")
            raise WebcamUnavailableError("Webcam bulunamadı, kullanımda veya erişilemiyor")

        reported_fps = float(capture.fps)
        if not math.isfinite(reported_fps) or reported_fps <= 0:
            reported_fps = None
        started_at = self._utc_now()
        session_id = str(uuid4())
        metadata = WebcamMetadata(
            source_id=self.source_id,
            session_id=session_id,
            device_index=self.device_index,
            reported_fps=reported_fps,
            width=capture.width,
            height=capture.height,
            started_at_utc=started_at,
        )
        with self._lock:
            self._active_session_id = session_id
            self._snapshot = WebcamStatusSnapshot(
                source_id=self.source_id,
                device_index=self.device_index,
                status=WebcamStatus.STREAMING,
                message="Webcam açıldı; ilk kare bekleniyor",
                session_id=session_id,
                frame_count=0,
                last_frame_at_utc=None,
            )
        return WebcamSession(
            metadata=metadata,
            capture=capture,
            status_callback=self._set_status,
            monotonic=self._monotonic,
            utc_now=self._utc_now,
        )
