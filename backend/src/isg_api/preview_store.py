"""Analizden bağımsız, tek kopya son-kare önizleme deposu."""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path


class PreviewState(StrEnum):
    LIVE = "live"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class PreviewSnapshot:
    camera_id: uuid.UUID
    state: PreviewState
    captured_at: datetime | None
    age_seconds: float | None
    size_bytes: int | None
    path: Path | None


class FilesystemPreviewStore:
    """Her kamera için yalnız en son JPEG'i atomik ad değişimiyle paylaşır."""

    def __init__(
        self,
        root: Path,
        *,
        stale_after_seconds: float = 3.0,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if stale_after_seconds <= 0:
            raise ValueError("Önizleme eskime eşiği pozitif olmalıdır")
        self.root = root.resolve()
        self.stale_after_seconds = stale_after_seconds
        self._utc_now = utc_now

    def publish(
        self,
        camera_id: uuid.UUID,
        jpeg_bytes: bytes,
        *,
        captured_at: datetime,
    ) -> PreviewSnapshot:
        if captured_at.tzinfo is None or captured_at.utcoffset() is None:
            raise ValueError("Önizleme zamanı saat dilimi içermelidir")
        if not jpeg_bytes.startswith(b"\xff\xd8") or not jpeg_bytes.endswith(b"\xff\xd9"):
            raise ValueError("Önizleme geçerli JPEG sınır işaretlerini taşımıyor")
        self.root.mkdir(parents=True, exist_ok=True)
        final_path = self._path(camera_id)
        temporary_path = self.root / f".{camera_id}.{uuid.uuid4().hex}.part"
        try:
            temporary_path.write_bytes(jpeg_bytes)
            timestamp = captured_at.timestamp()
            os.utime(temporary_path, (timestamp, timestamp))
            os.replace(temporary_path, final_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
        return self.snapshot(camera_id)

    def snapshot(self, camera_id: uuid.UUID) -> PreviewSnapshot:
        path = self._path(camera_id)
        try:
            stat = path.stat()
        except FileNotFoundError:
            return PreviewSnapshot(
                camera_id=camera_id,
                state=PreviewState.UNAVAILABLE,
                captured_at=None,
                age_seconds=None,
                size_bytes=None,
                path=None,
            )
        captured_at = datetime.fromtimestamp(stat.st_mtime, UTC)
        age_seconds = max(0.0, (self._utc_now() - captured_at).total_seconds())
        state = PreviewState.STALE if age_seconds > self.stale_after_seconds else PreviewState.LIVE
        return PreviewSnapshot(
            camera_id=camera_id,
            state=state,
            captured_at=captured_at,
            age_seconds=round(age_seconds, 3),
            size_bytes=stat.st_size,
            path=path,
        )

    def read(self, camera_id: uuid.UUID) -> tuple[PreviewSnapshot, bytes | None]:
        snapshot = self.snapshot(camera_id)
        if snapshot.path is None:
            return snapshot, None
        try:
            content = snapshot.path.read_bytes()
        except FileNotFoundError:
            return self.snapshot(camera_id), None
        return snapshot, content

    def _path(self, camera_id: uuid.UUID) -> Path:
        return self.root / f"{camera_id}.jpg"
