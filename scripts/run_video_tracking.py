"""Yerel PPE modelini kayıtlı videoda ByteTrack ile kısa süre çalıştırır."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from contextlib import closing
from pathlib import Path

from isg_api.ppe_tracking import AssignmentStatus, UltralyticsPpeTracker
from isg_api.video_source import RecordedVideoSource


def run_tracking(args: argparse.Namespace) -> dict:
    source = RecordedVideoSource(args.video, source_id=args.source_id)
    session = source.open_session()
    tracker = UltralyticsPpeTracker(
        args.model,
        device=args.device,
        confidence=args.confidence,
        image_size=args.image_size,
    )
    tracker.start_session(session.metadata.session_id)
    frame_count = 0
    unique_people: set[int] = set()
    assignment_counts = {status.value: 0 for status in AssignmentStatus}
    detection_counts: Counter[str] = Counter()
    tracked_detection_count = 0
    inference_times: list[float] = []

    with closing(session.frames(realtime=False)) as frames:
        for frame in frames:
            result = tracker.process_frame(frame)
            frame_count += 1
            inference_times.append(result.inference_ms)
            detection_counts.update(item.class_name for item in result.detections)
            tracked_detection_count += sum(
                item.track_id is not None for item in result.detections
            )
            unique_people.update(person.track_id for person in result.people)
            for assignment in result.assignments:
                assignment_counts[assignment.status.value] += 1
            if frame_count >= args.max_frames:
                break

    return {
        "source_id": session.metadata.source_id,
        "session_id": session.metadata.session_id,
        "video": str(session.metadata.path),
        "model": str(args.model.resolve()),
        "frames_processed": frame_count,
        "unique_person_track_ids": sorted(unique_people),
        "detection_counts": dict(sorted(detection_counts.items())),
        "tracked_detection_count": tracked_detection_count,
        "assignment_counts": assignment_counts,
        "average_inference_ms": (
            round(sum(inference_times) / len(inference_times), 3)
            if inference_times
            else None
        ),
        "images_or_video_saved": False,
        "warning": "Belirsiz atamalar hiçbir kişiye kesin ekipman olarak yazılmaz.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--source-id", default="demo-video")
    parser.add_argument("--max-frames", type=int, default=120)
    parser.add_argument("--device", default="0")
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--image-size", type=int, default=640)
    args = parser.parse_args()
    if args.max_frames <= 0:
        parser.error("max-frames sıfırdan büyük olmalıdır")
    if not args.video.is_file():
        parser.error(f"Video bulunamadı: {args.video}")
    if not args.model.is_file():
        parser.error(f"Yerel model bulunamadı; indirme yapılmadı: {args.model}")
    try:
        result = run_tracking(args)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
