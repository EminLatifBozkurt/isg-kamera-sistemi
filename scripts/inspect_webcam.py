"""Yerel webcam bağlantısını görüntü kaydetmeden kısa süre denetler."""

from __future__ import annotations

import argparse
import json
from contextlib import closing

from isg_api.webcam_source import WebcamSource


def inspect_webcam(device_index: int, *, source_id: str, max_frames: int) -> dict:
    """Webcam'i açar, sınırlı kare okur ve hiçbir görüntüyü diske yazmaz."""
    source = WebcamSource(device_index, source_id=source_id)
    session = source.open_session()
    read_frame_count = 0
    first_elapsed = None
    last_elapsed = None

    with closing(session.frames()) as frames:
        for frame in frames:
            if first_elapsed is None:
                first_elapsed = frame.source_timestamp_seconds
            last_elapsed = frame.source_timestamp_seconds
            read_frame_count += 1
            if read_frame_count >= max_frames:
                break

    metadata = session.metadata
    status = source.status
    return {
        "source_id": metadata.source_id,
        "session_id": metadata.session_id,
        "tracking_scope": f"{metadata.source_id}:{metadata.session_id}",
        "device_index": metadata.device_index,
        "reported_fps": metadata.reported_fps,
        "resolution": [metadata.width, metadata.height],
        "read_frame_count": read_frame_count,
        "first_elapsed_seconds": first_elapsed,
        "last_elapsed_seconds": last_elapsed,
        "final_status": status.status,
        "status_message": status.message,
        "images_saved": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=int, default=0, help="Webcam aygıt numarası")
    parser.add_argument("--source-id", default="webcam-0", help="Kaynak kimliği")
    parser.add_argument(
        "--max-frames", type=int, default=60, help="Okunduktan sonra durulacak kare"
    )
    args = parser.parse_args()
    if args.device < 0:
        parser.error("device negatif olamaz")
    if args.max_frames <= 0:
        parser.error("max-frames sıfırdan büyük olmalıdır")

    try:
        result = inspect_webcam(
            args.device,
            source_id=args.source_id,
            max_frames=args.max_frames,
        )
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
