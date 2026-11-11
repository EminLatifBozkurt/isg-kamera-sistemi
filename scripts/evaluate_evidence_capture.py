"""E3 tamponunu gerçek JPEG ve MP4 üretimiyle geçici klasörde doğrular."""

from __future__ import annotations

import json
import sys
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = ROOT / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from isg_api.evidence_capture import (
    EncodedEvidenceFrame,
    EvidenceCaptureManager,
    EvidencePolicy,
    FilesystemEvidenceWriter,
)


def make_frame(second: float) -> EncodedEvidenceFrame:
    image = np.zeros((180, 320, 3), dtype=np.uint8)
    image[:, :] = (25, 45, 70)
    cv2.rectangle(
        image,
        (30 + round(second * 40), 40),
        (110 + round(second * 40), 155),
        (0, 180, 255),
        -1,
    )
    cv2.putText(
        image,
        f"t={second:.1f}s",
        (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
    )
    success, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not success:
        raise RuntimeError("Deney karesi JPEG olarak kodlanamadı")
    return EncodedEvidenceFrame(
        session_id="e3-demo-session",
        source_timestamp_seconds=second,
        observed_at_utc=datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
        + timedelta(seconds=second),
        jpeg_bytes=encoded.tobytes(),
        width=320,
        height=180,
    )


def main() -> None:
    event_id = uuid.UUID("00000000-0000-0000-0000-0000000000e3")
    with tempfile.TemporaryDirectory(prefix="isg-e3-") as temporary_directory:
        media_root = Path(temporary_directory)
        manager = EvidenceCaptureManager(
            FilesystemEvidenceWriter(media_root),
            EvidencePolicy(
                pre_event_seconds=0.6,
                post_event_seconds=0.6,
                max_buffer_frames=20,
                max_buffer_bytes=4 * 1024 * 1024,
            ),
        )
        try:
            manager.start_session("e3-demo-session")
            for second in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
                manager.ingest(make_frame(second))
            manager.start_event(
                event_id,
                session_id="e3-demo-session",
                event_source_time=1.0,
            )
            for second in (1.2, 1.4, 1.6):
                manager.ingest(make_frame(second))

            finished = manager.wait_until_finished(event_id)
            if finished.result is None:
                raise RuntimeError(f"Kanıt üretilemedi: {finished.error_message}")
            snapshot_path = media_root / finished.result.snapshot.relative_path
            clip_path = media_root / finished.result.clip.relative_path
            capture = cv2.VideoCapture(str(clip_path))
            try:
                clip_opened = bool(capture.isOpened())
                decoded_frames = round(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            finally:
                capture.release()

            print(
                json.dumps(
                    {
                        "status": finished.status,
                        "completion_reason": finished.completion_reason,
                        "is_partial": finished.is_partial,
                        "buffered_clip_frames": finished.clip_frame_count,
                        "snapshot_exists": snapshot_path.is_file(),
                        "snapshot_bytes": snapshot_path.stat().st_size,
                        "clip_exists": clip_path.is_file(),
                        "clip_bytes": clip_path.stat().st_size,
                        "clip_opened": clip_opened,
                        "decoded_clip_frames": decoded_frames,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            manager.end_session("e3-demo-session")
        finally:
            manager.close()


if __name__ == "__main__":
    main()
