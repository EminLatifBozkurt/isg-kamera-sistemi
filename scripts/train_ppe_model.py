"""Yerel başlangıç ağırlığıyla küçük PPE algılama modelini eğitir.

Betik hiçbir model veya veri dosyasını otomatik indirmez. Eğitim ayarlarını,
girdi özetlerini ve oluşan ağırlık yollarını deney klasörüne JSON olarak yazar.
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

RUN_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def sha256(path: Path) -> str:
    """Deneyde kullanılan dosyanın değişmediğini kontrol etmek için özet üretir."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_run_name(name: str) -> str:
    """Deney adının yalnız güvenli dosya adı karakterleri içermesini sağlar."""
    if not RUN_NAME_PATTERN.fullmatch(name):
        raise ValueError(
            "Deney adı harf/rakamla başlamalı; yalnız harf, rakam, nokta, "
            "alt çizgi ve tire içermelidir"
        )
    return name


def validate_resume_checkpoint(run_dir: Path, resume_from: Path) -> Path:
    """Yalnız seçilen deneyin optimizer içeren last.pt kaydına izin verir."""
    checkpoint = resume_from.resolve()
    expected = (run_dir / "weights" / "last.pt").resolve()
    if checkpoint != expected:
        raise ValueError(
            "Devam ağırlığı seçilen deneyin weights/last.pt dosyası olmalıdır: "
            f"{expected}"
        )
    return checkpoint


def read_split_provenance(data_yaml: Path) -> dict:
    """Varsa B5 ayırma raporundan veri kaynağı bilgisini alır."""
    report_path = data_yaml.with_name("split-report.json")
    if not report_path.is_file():
        return {"split_report": None}
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return {
        "split_report": str(report_path.resolve()),
        "source_archive": report.get("source_archive"),
        "source_sha256": report.get("source_sha256"),
        "image_count": report.get("image_count"),
        "group_count": report.get("group_count"),
        "prepared_split_images": report.get("prepared_split_images"),
        "prepared_cross_split_similar_pairs": report.get(
            "prepared_cross_split_similar_pairs"
        ),
    }


def run_training(args: argparse.Namespace) -> dict:
    """Ultralytics eğitimini çalıştırır ve yeniden üretilebilir kayıt döndürür."""
    project_root = Path(__file__).resolve().parents[1]
    config_dir = project_root / "data" / "ultralytics-config"
    matplotlib_dir = project_root / "data" / "matplotlib-config"
    config_dir.mkdir(parents=True, exist_ok=True)
    matplotlib_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("YOLO_CONFIG_DIR", str(config_dir.resolve()))
    os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_dir.resolve()))

    import cv2
    import torch
    import ultralytics
    import ultralytics.utils as ultralytics_utils
    from ultralytics import YOLO
    from ultralytics.data.utils import check_det_dataset

    # Ultralytics AMP kontrolü sabit bir yolo26n.pt arar. Kendi onaylı yerel
    # ağırlık klasörümüzü göstererek gizli bir ağ indirme girişimini engelliyoruz.
    ultralytics_utils.WEIGHTS_DIR = args.model.resolve().parent

    output_root = args.output_root.resolve()
    run_dir = output_root / args.name
    # Eğitim sırasında last.pt dosyası güncelleneceği için başlangıç özetini
    # çalıştırmadan önce alıyoruz. Böylece hangi kayıttan devam edildiği kanıtlanır.
    resume_from_sha256 = (
        sha256(args.resume_from) if args.resume_from is not None else None
    )
    if args.resume_from is None and run_dir.exists():
        raise ValueError(f"Deney klasörü zaten var; üzerine yazılmadı: {run_dir}")
    if args.resume_from is not None:
        validate_resume_checkpoint(run_dir, args.resume_from)

    # autodownload=False yanlış/verilmeyen veri yolunda internet kullanımını önler.
    dataset = check_det_dataset(str(args.data.resolve()), autodownload=False)
    started_at = time.time()
    if args.resume_from is not None:
        # Checkpoint, önceki optimizer ve tur bilgisini içerir; aynı deney sürer.
        model = YOLO(str(args.resume_from.resolve()))
        metrics = model.train(resume=True)
    else:
        model = YOLO(str(args.model.resolve()))
        metrics = model.train(
            data=str(args.data.resolve()),
            epochs=args.epochs,
            imgsz=args.image_size,
            batch=args.batch,
            device=args.device,
            workers=args.workers,
            patience=args.patience,
            seed=args.seed,
            deterministic=True,
            project=str(output_root),
            name=args.name,
            exist_ok=False,
            cache=False,
            amp=True,
            plots=True,
            val=True,
            verbose=True,
        )
    duration_seconds = round(time.time() - started_at, 3)

    save_dir = Path(getattr(metrics, "save_dir", run_dir)).resolve()
    weights_dir = save_dir / "weights"
    best_path = weights_dir / "best.pt"
    last_path = weights_dir / "last.pt"
    results = getattr(metrics, "results_dict", {})
    serializable_results = {
        str(key): float(value) if hasattr(value, "__float__") else value
        for key, value in results.items()
    }

    record = {
        "experiment": {
            "name": args.name,
            "started_unix": round(started_at, 3),
            "duration_seconds": duration_seconds,
            "output_dir": str(save_dir),
        },
        "inputs": {
            "model": str(args.model.resolve()),
            "model_sha256": sha256(args.model),
            "data_yaml": str(args.data.resolve()),
            "data_yaml_sha256": sha256(args.data),
            "resume_from": str(args.resume_from.resolve())
            if args.resume_from is not None
            else None,
            "resume_from_sha256": resume_from_sha256,
            "dataset_train": str(dataset["train"]),
            "dataset_val": str(dataset["val"]),
            "dataset_test": str(dataset.get("test")),
            "class_count": dataset["nc"],
            "split_provenance": read_split_provenance(args.data),
        },
        "settings": {
            "epochs": args.epochs,
            "image_size": args.image_size,
            "batch": args.batch,
            "device": args.device,
            "workers": args.workers,
            "patience": args.patience,
            "seed": args.seed,
            "deterministic": True,
            "cache": False,
            "amp": True,
        },
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "ultralytics": ultralytics.__version__,
            "opencv": cv2.__version__,
            "cuda_runtime": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
        "outputs": {
            "best_weights": str(best_path) if best_path.is_file() else None,
            "best_weights_sha256": sha256(best_path) if best_path.is_file() else None,
            "last_weights": str(last_path) if last_path.is_file() else None,
            "last_weights_sha256": sha256(last_path) if last_path.is_file() else None,
        },
        "validation_metrics": serializable_results,
        "warning": (
            "Bu bir temel deneydir. Doğruluk ve saha uygunluğu bağımsız test "
            "bölümünde B7 aşamasında değerlendirilecektir."
        ),
    }
    record_path = save_dir / "experiment-record.json"
    record_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model", required=True, type=Path, help="Yerel .pt başlangıç ağırlığı"
    )
    parser.add_argument(
        "--data", required=True, type=Path, help="Hazırlanmış data.yaml"
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/training/b6"),
        help="Git dışında tutulacak eğitim kök klasörü",
    )
    parser.add_argument("--name", required=True, help="Benzersiz deney adı")
    parser.add_argument(
        "--resume-from",
        type=Path,
        help="Aynı deneyin yerel weights/last.pt kaydından devam et",
    )
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--device", default="0", help="Ultralytics aygıtı: 0 veya cpu")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20261109)
    args = parser.parse_args()

    try:
        args.name = validate_run_name(args.name)
    except ValueError as error:
        parser.error(str(error))
    if not args.model.is_file():
        parser.error(
            f"Yerel model bulunamadı; otomatik indirme yapılmadı: {args.model}"
        )
    if not args.data.is_file():
        parser.error(f"Veri tanımı bulunamadı: {args.data}")
    if args.resume_from is not None and not args.resume_from.is_file():
        parser.error(f"Devam ağırlığı bulunamadı: {args.resume_from}")
    if args.epochs <= 0 or args.image_size <= 0 or args.batch == 0:
        parser.error("epochs ve image-size pozitif, batch sıfırdan farklı olmalıdır")
    if args.workers < 0 or args.patience < 0:
        parser.error("workers ve patience negatif olamaz")

    try:
        record = run_training(args)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
