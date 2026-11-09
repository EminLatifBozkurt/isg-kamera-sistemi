"""Kayıtlı videoyu kaynak zamanı ve bağımsız oturum kimliğiyle okur."""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4


class VideoCapture(Protocol):
    """OpenCV ayrıntılarını oturum mantığından ayıran küçük arayüz."""

    @property
    def is_opened(self) -> bool: ...

    @property
    def fps(self) -> float: ...

    @property
    def frame_count(self) -> int | None: ...

    @property
    def width(self) -> int | None: ...

    @property
    def height(self) -> int | None: ...

    @property
    def position_seconds(self) -> float | None: ...

    def read(self) -> tuple[bool, Any]: ...

    def release(self) -> None: ...


class OpenCvVideoCapture:
    """OpenCV VideoCapture nesnesini yukarıdaki yerel arayüze uyarlar."""

    def __init__(self, path: Path) -> None:
        # Sunucu, video özelliği kullanılmadığında OpenCV'ye bağımlı kalmasın.
        import cv2

        self._cv2 = cv2
        self._capture = cv2.VideoCapture(str(path))

    @property
    def is_opened(self) -> bool:
        return bool(self._capture.isOpened())

    def _positive_integer_property(self, property_id: int) -> int | None:
        value = float(self._capture.get(property_id))
        return round(value) if math.isfinite(value) and value > 0 else None

    @property
    def fps(self) -> float:
        return float(self._capture.get(self._cv2.CAP_PROP_FPS))

    @property
    def frame_count(self) -> int | None:
        return self._positive_integer_property(self._cv2.CAP_PROP_FRAME_COUNT)

    @property
    def width(self) -> int | None:
        return self._positive_integer_property(self._cv2.CAP_PROP_FRAME_WIDTH)

    @property
    def height(self) -> int | None:
        return self._positive_integer_property(self._cv2.CAP_PROP_FRAME_HEIGHT)

    @property
    def position_seconds(self) -> float | None:
        milliseconds = float(self._capture.get(self._cv2.CAP_PROP_POS_MSEC))
        if not math.isfinite(milliseconds) or milliseconds < 0:
            return None
        return milliseconds / 1000.0

    def read(self) -> tuple[bool, Any]:
        return self._capture.read()

    def release(self) -> None:
        self._capture.release()


class VideoSessionStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class VideoFrame:
    """Bir görüntü ile görüntünün kaynağa ve oturuma ait kimlik bilgileri."""

    source_id: str
    session_id: str
    frame_index: int
    source_timestamp_seconds: float
    observed_at_utc: datetime
    image: Any

    @property
    def tracking_scope(self) -> str:
        """Takip numaralarının başka video oturumlarıyla karışmasını engeller."""
        return f"{self.source_id}:{self.session_id}"


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    source_id: str
    session_id: str
    path: Path
    fps: float
    frame_count: int | None
    width: int | None
    height: int | None
    started_at_utc: datetime


class RecordedVideoSession:
    """Tek kullanımlık video oturumu; her açılışta yeni kimlik ve zaman sıfırı."""

    def __init__(
        self,
        *,
        source_id: str,
        path: Path,
        capture: VideoCapture,
        playback_speed: float,
        monotonic: Callable[[], float],
        sleeper: Callable[[float], None],
        utc_now: Callable[[], datetime],
    ) -> None:
        self._capture = capture
        self._playback_speed = playback_speed
        self._monotonic = monotonic
        self._sleeper = sleeper
        self._utc_now = utc_now
        self._used = False
        self.status = VideoSessionStatus.CREATED
        self.metadata = VideoMetadata(
            source_id=source_id,
            session_id=str(uuid4()),
            path=path,
            fps=capture.fps,
            frame_count=capture.frame_count,
            width=capture.width,
            height=capture.height,
            started_at_utc=utc_now(),
        )

    def _source_timestamp(self, frame_index: int, previous: float | None) -> float:
        """Kapsayıcı zamanı bozuksa kare hızı tabanlı güvenli zamana döner."""
        fallback = frame_index / self.metadata.fps
        reported = self._capture.position_seconds
        if reported is None or not math.isfinite(reported) or reported < 0:
            return fallback
        if previous is not None and reported <= previous:
            return fallback
        return reported

    def frames(self, *, realtime: bool = True) -> Iterator[VideoFrame]:
        """Kareleri video zamanına göre verir; aynı oturum ikinci kez okunamaz."""
        if self._used:
            raise RuntimeError("Video oturumu tek kullanımlıktır; yeni oturum açılmalı")
        self._used = True
        self.status = VideoSessionStatus.RUNNING
        playback_started = self._monotonic()
        first_source_timestamp: float | None = None
        previous_timestamp: float | None = None
        frame_index = 0

        try:
            while True:
                success, image = self._capture.read()
                if not success:
                    self.status = VideoSessionStatus.COMPLETED
                    break

                source_timestamp = self._source_timestamp(frame_index, previous_timestamp)
                if first_source_timestamp is None:
                    first_source_timestamp = source_timestamp
                if realtime:
                    source_elapsed = source_timestamp - first_source_timestamp
                    target_elapsed = source_elapsed / self._playback_speed
                    wait_seconds = target_elapsed - (self._monotonic() - playback_started)
                    if wait_seconds > 0:
                        self._sleeper(wait_seconds)

                yield VideoFrame(
                    source_id=self.metadata.source_id,
                    session_id=self.metadata.session_id,
                    frame_index=frame_index,
                    source_timestamp_seconds=source_timestamp,
                    observed_at_utc=self._utc_now(),
                    image=image,
                )
                previous_timestamp = source_timestamp
                frame_index += 1
        except Exception:
            self.status = VideoSessionStatus.FAILED
            raise
        finally:
            self._capture.release()
            if self.status is VideoSessionStatus.RUNNING:
                self.status = VideoSessionStatus.STOPPED


class RecordedVideoSource:
    """Aynı kayıtlı videodan birbirinden bağımsız oturumlar oluşturur."""

    def __init__(
        self,
        path: Path,
        *,
        source_id: str,
        playback_speed: float = 1.0,
        capture_factory: Callable[[Path], VideoCapture] = OpenCvVideoCapture,
        monotonic: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        source_id = source_id.strip()
        if not source_id:
            raise ValueError("Kaynak kimliği boş olamaz")
        if not math.isfinite(playback_speed) or playback_speed <= 0:
            raise ValueError("Oynatma hızı sıfırdan büyük ve sonlu olmalıdır")
        self.path = path.resolve()
        self.source_id = source_id
        self.playback_speed = playback_speed
        self._capture_factory = capture_factory
        self._monotonic = monotonic
        self._sleeper = sleeper
        self._utc_now = utc_now

    def open_session(self) -> RecordedVideoSession:
        """Dosyayı açar; her çağrı yeni oturum kimliği ve boş durum üretir."""
        if not self.path.is_file():
            raise ValueError(f"Video dosyası bulunamadı: {self.path}")
        capture = self._capture_factory(self.path)
        if not capture.is_opened:
            capture.release()
            raise ValueError(f"Video açılamadı veya biçim desteklenmiyor: {self.path}")
        fps = float(capture.fps)
        if not math.isfinite(fps) or fps <= 0:
            capture.release()
            raise ValueError("Videonun geçerli kare hızı (FPS) okunamadı")
        return RecordedVideoSession(
            source_id=self.source_id,
            path=self.path,
            capture=capture,
            playback_speed=self.playback_speed,
            monotonic=self._monotonic,
            sleeper=self._sleeper,
            utc_now=self._utc_now,
        )
