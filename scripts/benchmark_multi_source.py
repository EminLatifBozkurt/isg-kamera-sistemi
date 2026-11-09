"""Bir ve iki yerel video kaynağında PPE takip kapasitesini karşılaştırır."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import time
from pathlib import Path

os.environ.setdefault("YOLO_AUTOINSTALL", "False")

from isg_api.ppe_tracking import UltralyticsPpeTracker
from isg_api.video_source import RecordedVideoSource


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def supported_source_count(results: list[dict], target_fps: float) -> int:
    """Bütün kaynakları hedef hıza ulaşan en büyük senaryoyu döndürür."""
    supported = 0
    for result in results:
        if result["minimum_source_fps"] >= target_fps:
            supported = max(supported, int(result["source_count"]))
    return supported


def benchmark_scenario(
    *,
    source_count: int,
    video: Path,
    model: Path,
    warmup_frames: int,
    measured_frames: int,
    device: str,
) -> dict:
    import torch

    sources = [
        RecordedVideoSource(video, source_id=f"benchmark-{index + 1}")
        for index in range(source_count)
    ]
    sessions = [source.open_session() for source in sources]
    iterators = [session.frames(realtime=False) for session in sessions]
    trackers = [UltralyticsPpeTracker(model, device=device) for _ in sessions]
    for tracker, session in zip(trackers, sessions, strict=True):
        tracker.start_session(session.metadata.session_id)

    per_source_counts = [0] * source_count
    inference_times: list[float] = []
    try:
        for _ in range(warmup_frames):
            for iterator, tracker in zip(iterators, trackers, strict=True):
                tracker.process_frame(next(iterator))
        if torch.cuda.is_available():
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        for _ in range(measured_frames):
            for index, (iterator, tracker) in enumerate(
                zip(iterators, trackers, strict=True)
            ):
                result = tracker.process_frame(next(iterator))
                per_source_counts[index] += 1
                inference_times.append(result.inference_ms)
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - started
    except StopIteration as error:
        raise ValueError(
            "Video ısınma ve ölçüm kareleri için yeterince uzun değil"
        ) from error
    finally:
        for iterator in iterators:
            iterator.close()

    source_fps = [round(count / elapsed, 3) for count in per_source_counts]
    result = {
        "source_count": source_count,
        "warmup_frames_per_source": warmup_frames,
        "measured_frames_per_source": measured_frames,
        "elapsed_seconds": round(elapsed, 3),
        "total_fps": round(sum(per_source_counts) / elapsed, 3),
        "source_fps": source_fps,
        "minimum_source_fps": min(source_fps),
        "average_tracker_call_ms": round(
            sum(inference_times) / len(inference_times), 3
        ),
        "cuda_peak_allocated_mib": (
            round(torch.cuda.max_memory_allocated() / 1024**2, 3)
            if torch.cuda.is_available()
            else None
        ),
        "cuda_peak_reserved_mib": (
            round(torch.cuda.max_memory_reserved() / 1024**2, 3)
            if torch.cuda.is_available()
            else None
        ),
    }
    del trackers, sessions, sources
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return result


def run_benchmark(args: argparse.Namespace) -> dict:
    import cv2
    import torch
    import ultralytics

    output_dir = args.output_root.resolve() / args.name
    if output_dir.exists():
        raise ValueError(f"Ölçüm klasörü zaten var; üzerine yazılmadı: {output_dir}")
    results = [
        benchmark_scenario(
            source_count=count,
            video=args.video.resolve(),
            model=args.model.resolve(),
            warmup_frames=args.warmup_frames,
            measured_frames=args.measured_frames,
            device=args.device,
        )
        for count in args.source_counts
    ]
    supported = supported_source_count(results, args.target_fps)
    max_tested = max(args.source_counts)
    report = {
        "inputs": {
            "video": str(args.video.resolve()),
            "video_sha256": sha256(args.video),
            "model": str(args.model.resolve()),
            "model_sha256": sha256(args.model),
            "image_size": 640,
            "device": args.device,
        },
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "ultralytics": ultralytics.__version__,
            "opencv": cv2.__version__,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
        "target_fps_per_source": args.target_fps,
        "maximum_tested_source_count": max_tested,
        "results": results,
        "supported_simultaneous_sources_at_target": supported,
        "network_stream_status": "not_enabled_without_real_rtsp_measurement",
        "decision": (
            f"En fazla {max_tested} kaynak denendi. Bu ölçüm ve {args.target_fps:g} "
            f"FPS hedefiyle yapılandırılacak eşzamanlı kaynak sınırı: {supported}. "
            "Daha fazla kaynak destekleniyor sonucu çıkarılamaz. Gerçek RTSP ölçümü "
            "yapılmadığı için ağ akışı şimdilik etkinleştirilmez."
        ),
        "warning": (
            "Sonuç bu bilgisayar, model, çözünürlük ve kısa yerel video içindir; "
            "gerçek saha kabulü değildir."
        ),
    }
    output_dir.mkdir(parents=True)
    (output_dir / "c5-capacity-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--source-counts", nargs="+", type=int, default=[1, 2])
    parser.add_argument("--warmup-frames", type=int, default=3)
    parser.add_argument("--measured-frames", type=int, default=12)
    parser.add_argument("--target-fps", type=float, default=5.0)
    parser.add_argument("--device", default="0")
    parser.add_argument("--output-root", type=Path, default=Path("data/evaluation/c5"))
    args = parser.parse_args()
    if not args.video.is_file() or not args.model.is_file():
        parser.error("Yerel video veya model bulunamadı; indirme yapılmadı")
    if (
        not args.source_counts
        or any(count <= 0 for count in args.source_counts)
        or args.warmup_frames < 0
        or args.measured_frames <= 0
        or args.target_fps <= 0
    ):
        parser.error("Kaynak, kare ve FPS değerleri pozitif olmalıdır")
    if len(set(args.source_counts)) != len(args.source_counts):
        parser.error("source-counts yinelenen değer içeremez")
    try:
        report = run_benchmark(args)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
