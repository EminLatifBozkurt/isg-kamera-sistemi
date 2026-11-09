"""Yerel bir videonun zaman ve oturum bilgilerinin okunabildiğini denetler."""

from __future__ import annotations

import argparse
import json
from contextlib import closing
from pathlib import Path

from isg_api.video_source import RecordedVideoSource


def inspect_video(
    path: Path, *, source_id: str, max_frames: int, realtime: bool
) -> dict:
    """Model çalıştırmadan sınırlı sayıda kareyi okuyup özet döndürür."""
    source = RecordedVideoSource(path, source_id=source_id)
    session = source.open_session()
    frame_count = 0
    first_timestamp = None
    last_timestamp = None

    with closing(session.frames(realtime=realtime)) as frames:
        for frame in frames:
            if first_timestamp is None:
                first_timestamp = frame.source_timestamp_seconds
            last_timestamp = frame.source_timestamp_seconds
            frame_count += 1
            if frame_count >= max_frames:
                break

    metadata = session.metadata
    return {
        "source_id": metadata.source_id,
        "session_id": metadata.session_id,
        "tracking_scope": f"{metadata.source_id}:{metadata.session_id}",
        "path": str(metadata.path),
        "fps": metadata.fps,
        "declared_frame_count": metadata.frame_count,
        "resolution": [metadata.width, metadata.height],
        "read_frame_count": frame_count,
        "first_source_timestamp_seconds": first_timestamp,
        "last_source_timestamp_seconds": last_timestamp,
        "status": session.status,
        "realtime": realtime,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Yerel video dosyası")
    parser.add_argument("--source-id", default="demo-video", help="Kaynak kimliği")
    parser.add_argument(
        "--max-frames", type=int, default=120, help="En fazla okunacak kare"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Kaynak hızını beklemeden kareleri olabildiğince hızlı oku",
    )
    args = parser.parse_args()
    if args.max_frames <= 0:
        parser.error("max-frames sıfırdan büyük olmalıdır")

    try:
        result = inspect_video(
            args.video,
            source_id=args.source_id,
            max_frames=args.max_frames,
            realtime=not args.fast,
        )
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
