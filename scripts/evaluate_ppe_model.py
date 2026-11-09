"""Yerel PPE modelini dokunulmamış test bölümünde ölçer.

Betik model veya veri indirmez. Sınıf başına başarı, görüntü başına süre ve
CUDA tepe bellek kullanımını JSON raporuna yazar.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import time
from pathlib import Path

if __package__:
    from scripts.offline_ultralytics import ensure_local_ultralytics_font
else:
    from offline_ultralytics import ensure_local_ultralytics_font

IMAGE_SUFFIXES = {
    ".bmp",
    ".dng",
    ".jpeg",
    ".jpg",
    ".mpo",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}
RUN_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def sha256(path: Path) -> str:
    """Ölçülen model ve veri tanımının dosya özetini üretir."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_run_name(name: str) -> str:
    """Ölçüm adının çıktı klasörü dışına çıkmasını engeller."""
    if not RUN_NAME_PATTERN.fullmatch(name):
        raise ValueError(
            "Ölçüm adı harf/rakamla başlamalı; yalnız harf, rakam, nokta, "
            "alt çizgi ve tire içermelidir"
        )
    return name


def count_images(path: Path) -> int:
    """Bir klasördeki desteklenen görüntüleri alt klasörleriyle birlikte sayar."""
    if not path.is_dir():
        raise ValueError(f"Test görüntü klasörü bulunamadı: {path}")
    return sum(
        1
        for candidate in path.rglob("*")
        if candidate.is_file() and candidate.suffix.lower() in IMAGE_SUFFIXES
    )


def find_weak_classes(rows: list[dict], map50_threshold: float) -> list[str]:
    """Seçilen mAP50 eşiğinin altında kalan, etiketi bulunan sınıfları döndürür."""
    return [
        str(row["Class"])
        for row in rows
        if int(row["Instances"]) > 0 and float(row["mAP50"]) < map50_threshold
    ]


def calculate_runtime(speed: dict[str, float]) -> dict[str, float | None]:
    """Ultralytics sürelerinden uçtan uca görüntü süresi ve yaklaşık FPS hesaplar."""
    parts = ("preprocess", "inference", "postprocess")
    total_ms = sum(float(speed.get(part, 0.0)) for part in parts)
    return {
        "preprocess_ms_per_image": round(float(speed.get("preprocess", 0.0)), 4),
        "inference_ms_per_image": round(float(speed.get("inference", 0.0)), 4),
        "postprocess_ms_per_image": round(float(speed.get("postprocess", 0.0)), 4),
        "pipeline_ms_per_image": round(total_ms, 4),
        "approx_pipeline_fps": round(1000.0 / total_ms, 3) if total_ms > 0 else None,
    }


def to_json_value(value):
    """NumPy gibi kütüphane sayılarını standart JSON türlerine dönüştürür."""
    if isinstance(value, dict):
        return {str(key): to_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_value(item) for item in value]
    item_method = getattr(value, "item", None)
    return to_json_value(item_method()) if callable(item_method) else value


def run_evaluation(args: argparse.Namespace) -> dict:
    """Test değerlendirmesini çalıştırır ve tekrar üretilebilir kayıt döndürür."""
    project_root = Path(__file__).resolve().parents[1]
    config_dir = project_root / "data" / "ultralytics-config"
    matplotlib_dir = project_root / "data" / "matplotlib-config"
    config_dir.mkdir(parents=True, exist_ok=True)
    matplotlib_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("YOLO_CONFIG_DIR", str(config_dir.resolve()))
    os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_dir.resolve()))
    # Ultralytics doğrulama başında Arial.ttf arayabilir. Yerel sistem fontunu
    # önceden hazırlayarak arka plandaki küçük font indirmesini de engelliyoruz.
    ensure_local_ultralytics_font(config_dir)

    import cv2
    import torch
    import ultralytics
    from ultralytics import YOLO
    from ultralytics.data.utils import check_det_dataset

    output_root = args.output_root.resolve()
    run_dir = output_root / args.name
    if run_dir.exists():
        raise ValueError(f"Ölçüm klasörü zaten var; üzerine yazılmadı: {run_dir}")

    # autodownload=False, veri yolu hatasında internetten veri aramayı engeller.
    dataset = check_det_dataset(str(args.data.resolve()), autodownload=False)
    test_value = dataset.get("test")
    if not test_value or isinstance(test_value, list):
        raise ValueError("data.yaml tek bir yerel test görüntü klasörü göstermelidir")
    test_dir = Path(test_value).resolve()
    test_image_count = count_images(test_dir)
    if test_image_count == 0:
        raise ValueError(f"Test bölümünde görüntü bulunamadı: {test_dir}")

    if args.device != "cpu" and not torch.cuda.is_available():
        raise RuntimeError("CUDA aygıtı istendi fakat PyTorch ekran kartını görmüyor")

    model = YOLO(str(args.model.resolve()))
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()

    started_at = time.time()
    metrics = model.val(
        data=str(args.data.resolve()),
        split="test",
        imgsz=args.image_size,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        project=str(output_root),
        name=args.name,
        exist_ok=False,
        plots=False,
        save_json=False,
        verbose=True,
    )
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    duration_seconds = round(time.time() - started_at, 3)

    peak_allocated_mib = None
    peak_reserved_mib = None
    if torch.cuda.is_available():
        mib = 1024 * 1024
        peak_allocated_mib = round(torch.cuda.max_memory_allocated() / mib, 3)
        peak_reserved_mib = round(torch.cuda.max_memory_reserved() / mib, 3)

    class_rows = to_json_value(metrics.summary(decimals=6))
    weak_classes = find_weak_classes(class_rows, args.weak_map50_threshold)
    overall = {
        str(key): round(float(value), 6) for key, value in metrics.results_dict.items()
    }
    save_dir = Path(getattr(metrics, "save_dir", run_dir)).resolve()
    record = {
        "evaluation": {
            "name": args.name,
            "split": "test",
            "duration_seconds": duration_seconds,
            "output_dir": str(save_dir),
        },
        "inputs": {
            "model": str(args.model.resolve()),
            "model_sha256": sha256(args.model),
            "data_yaml": str(args.data.resolve()),
            "data_yaml_sha256": sha256(args.data),
            "test_directory": str(test_dir),
            "test_image_count": test_image_count,
        },
        "settings": {
            "image_size": args.image_size,
            "batch": args.batch,
            "device": args.device,
            "workers": args.workers,
            "weak_map50_threshold": args.weak_map50_threshold,
            "plots": False,
        },
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "ultralytics": ultralytics.__version__,
            "opencv": cv2.__version__,
            "cuda_runtime": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
        "overall_metrics": overall,
        "class_metrics": class_rows,
        "runtime": calculate_runtime(metrics.speed),
        "gpu_memory": {
            "peak_allocated_mib": peak_allocated_mib,
            "peak_reserved_mib": peak_reserved_mib,
        },
        "review": {
            "weak_classes_below_map50_threshold": weak_classes,
            "note": (
                "Eşik yalnız zayıf sınıfları inceleme için işaretler; saha güvenliği "
                "veya üretim kullanımı için kabul eşiği değildir."
            ),
        },
        "warning": (
            "Bu sonuç yalnız ayrılmış test verisi ve bu bilgisayar için geçerlidir. "
            "Gerçek kamera açısı, ışık, örtülme ve video akışı ayrıca sınanmalıdır."
        ),
    }
    report_path = save_dir / "b7-test-report.json"
    report_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path, help="Yerel best.pt")
    parser.add_argument(
        "--data", required=True, type=Path, help="Hazırlanmış data.yaml"
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/evaluation/b7"),
        help="Git dışında tutulacak ölçüm kök klasörü",
    )
    parser.add_argument("--name", required=True, help="Benzersiz ölçüm adı")
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--device", default="0", help="Ultralytics aygıtı: 0 veya cpu")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--weak-map50-threshold", type=float, default=0.30)
    args = parser.parse_args()

    try:
        args.name = validate_run_name(args.name)
    except ValueError as error:
        parser.error(str(error))
    if not args.model.is_file():
        parser.error(f"Yerel model bulunamadı; indirme yapılmadı: {args.model}")
    if not args.data.is_file():
        parser.error(f"Veri tanımı bulunamadı: {args.data}")
    if args.image_size <= 0 or args.batch <= 0:
        parser.error("image-size ve batch pozitif olmalıdır")
    if args.workers < 0:
        parser.error("workers negatif olamaz")
    if not 0.0 <= args.weak_map50_threshold <= 1.0:
        parser.error("weak-map50-threshold 0 ile 1 arasında olmalıdır")

    try:
        record = run_evaluation(args)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
