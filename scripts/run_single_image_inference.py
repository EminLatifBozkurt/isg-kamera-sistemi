"""ZIP içindeki tek görüntüde yerel YOLO ağırlığıyla çıkarım yap.

Betik model dosyasını otomatik indirmez. Kaynak görüntüyü, işaretlenmiş sonucu
ve makinece okunabilir JSON raporunu Git dışında tutulan çıktı klasörüne yazar.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

if __package__:
    from scripts.offline_ultralytics import ensure_local_ultralytics_font
else:
    from offline_ultralytics import ensure_local_ultralytics_font


def parse_names(data_yaml: str) -> dict[int, str]:
    """Veri tanımındaki `0: helmet` biçimindeki sınıf adlarını oku."""
    names: dict[int, str] = {}
    inside_names = False
    for line in data_yaml.splitlines():
        if line.strip() == "names:":
            inside_names = True
            continue
        if not inside_names:
            continue
        match = re.match(r"^\s+(\d+):\s*([^#]+?)\s*$", line)
        if match:
            names[int(match.group(1))] = match.group(2).strip().strip("'\"")
        elif line and not line.startswith((" ", "\t", "#")):
            break
    if not names:
        raise ValueError("data.yaml içinde sınıf adları bulunamadı")
    return names


def matching_label_member(image_member: str) -> str:
    """images/test/a.jpg yolunu labels/test/a.txt yoluna dönüştür."""
    image_path = PurePosixPath(image_member)
    if not image_path.parts or image_path.parts[0] != "images":
        raise ValueError("Görüntü yolu images/ klasörü altında olmalıdır")
    return str(PurePosixPath("labels", *image_path.parts[1:]).with_suffix(".txt"))


def load_sample(archive: Path, image_member: str) -> tuple[object, Counter[str]]:
    """Görüntüyü ve aynı görüntünün gerçek PPE etiket sayılarını ZIP'ten oku."""
    import cv2
    import numpy as np

    with ZipFile(archive) as dataset:
        members = set(dataset.namelist())
        label_member = matching_label_member(image_member)
        required = {"data.yaml", image_member, label_member}
        missing = sorted(required - members)
        if missing:
            raise ValueError(f"Arşivde gerekli dosyalar yok: {', '.join(missing)}")

        class_names = parse_names(dataset.read("data.yaml").decode("utf-8-sig"))
        label_rows = dataset.read(label_member).decode("utf-8-sig").splitlines()
        class_counts: Counter[str] = Counter()
        for line_number, row in enumerate(label_rows, start=1):
            values = row.split()
            if len(values) != 5:
                raise ValueError(
                    f"Geçersiz etiket satırı: {label_member}:{line_number}"
                )
            class_id = int(values[0])
            if class_id not in class_names:
                raise ValueError(f"Bilinmeyen sınıf kimliği: {class_id}")
            class_counts[class_names[class_id]] += 1

        encoded_image = np.frombuffer(dataset.read(image_member), dtype=np.uint8)
        image = cv2.imdecode(encoded_image, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"Görüntü çözülemedi: {image_member}")
        return image, class_counts


def run_inference(args: argparse.Namespace) -> dict:
    """Yerel ağırlığı çalıştır ve karşılaştırılabilir raporu üret."""
    # Ultralytics ayarları da veri/model çıktıları gibi Git dışında tutulur.
    project_root = Path(__file__).resolve().parents[1]
    config_dir = project_root / "data" / "ultralytics-config"
    config_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("YOLO_CONFIG_DIR", str(config_dir.resolve()))
    ensure_local_ultralytics_font(config_dir)

    import cv2
    from ultralytics import YOLO

    image, ground_truth = load_sample(args.archive, args.image_member)
    model = YOLO(str(args.model))
    result = model.predict(
        source=image,
        device=args.device,
        imgsz=args.image_size,
        conf=args.confidence,
        verbose=False,
    )[0]

    detections = []
    if result.boxes is not None:
        class_ids = result.boxes.cls.int().cpu().tolist()
        confidences = result.boxes.conf.cpu().tolist()
        coordinates = result.boxes.xyxy.cpu().tolist()
        for class_id, confidence, xyxy in zip(
            class_ids, confidences, coordinates, strict=True
        ):
            detections.append(
                {
                    "class_id": class_id,
                    "class_name": result.names[class_id],
                    "confidence": round(confidence, 4),
                    "xyxy": [round(value, 2) for value in xyxy],
                }
            )

    model_class_names = {str(name).lower() for name in result.names.values()}
    ppe_classes = {"helmet", "gloves", "vest", "boots", "goggles"}
    unsupported_ppe_classes = sorted(ppe_classes - model_class_names)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = PurePosixPath(args.image_member).stem
    source_path = args.output_dir / f"{stem}-source.jpg"
    annotated_path = args.output_dir / f"{stem}-general-yolo.jpg"
    report_path = args.output_dir / f"{stem}-report.json"
    if not cv2.imwrite(str(source_path), image):
        raise OSError(f"Kaynak görüntü yazılamadı: {source_path}")
    if not cv2.imwrite(str(annotated_path), result.plot()):
        raise OSError(f"İşaretlenmiş görüntü yazılamadı: {annotated_path}")

    report = {
        "model": {
            "file": str(args.model),
            "task": model.task,
            "scope": "Genel nesne tespiti; PPE için özel eğitilmemiştir.",
        },
        "source": {
            "archive": str(args.archive),
            "image_member": args.image_member,
            "shape": list(image.shape),
        },
        "dataset_ground_truth": dict(sorted(ground_truth.items())),
        "general_model_detections": detections,
        "comparison": {
            "ppe_classes_missing_from_model_catalog": unsupported_ppe_classes,
            "meaning": (
                "Bu genel modelin helmet/vest gibi sınıfları üretmemesi, "
                "ekipmanın görüntüde olmadığı anlamına gelmez. PPE verisiyle "
                "eğitilmiş ayrı ağırlık gerekir."
            ),
        },
        "speed_ms": {key: round(value, 3) for key, value in result.speed.items()},
        "outputs": {
            "source_image": str(source_path),
            "annotated_image": str(annotated_path),
            "report": str(report_path),
        },
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Construction-PPE ZIP arşivi")
    parser.add_argument("image_member", help="Örnek: images/test/image999.jpg")
    parser.add_argument("--model", required=True, type=Path, help="Yerel .pt ağırlığı")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/inference/b4"),
        help="Git dışında tutulacak sonuç klasörü",
    )
    parser.add_argument("--device", default="0", help="Ultralytics aygıtı: 0 veya cpu")
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--confidence", type=float, default=0.25)
    args = parser.parse_args()

    # Otomatik indirmeye izin vermiyoruz; her dış dosya kullanıcı onayıyla alınır.
    if not args.archive.is_file():
        parser.error(f"Arşiv bulunamadı: {args.archive}")
    if not args.model.is_file():
        parser.error(
            f"Yerel model bulunamadı; otomatik indirme yapılmadı: {args.model}"
        )
    if not 0 < args.confidence <= 1:
        parser.error("confidence 0 ile 1 arasında olmalıdır")

    try:
        report = run_inference(args)
    except (BadZipFile, OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
