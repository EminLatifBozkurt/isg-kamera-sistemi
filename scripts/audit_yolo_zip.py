"""YOLO biçimindeki bir ZIP veri setinin yapısal sorunlarını raporlar.

Bu araç modeli eğitmez ve görüntüleri dışarı çıkarmaz. ZIP içindeki veri tanımını,
görüntü/etiket eşleşmesini ve normalize kutu büyüklüklerini inceler. Böylece veri
seti değişirse aynı kontrolleri yeniden çalıştırabiliriz.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dataset_key(member: str, prefix: str) -> str:
    """images/train/a.jpg ve labels/train/a.txt için aynı anahtarı üretir."""
    relative = member.removeprefix(prefix)
    return str(PurePosixPath(relative).with_suffix(""))


def parse_names(data_yaml: str) -> dict[int, str]:
    """Ultralytics YAML dosyasındaki `0: helmet` satırlarını ek paket olmadan okur."""
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


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    index = round((len(ordered) - 1) * ratio)
    return ordered[index]


def audit(archive: Path) -> dict:
    with ZipFile(archive) as dataset:
        members = dataset.namelist()
        if "data.yaml" not in members:
            raise ValueError("ZIP kökünde data.yaml bulunamadı")

        class_names = parse_names(dataset.read("data.yaml").decode("utf-8-sig"))
        image_members = [
            name
            for name in members
            if name.startswith("images/")
            and PurePosixPath(name).suffix.lower() in IMAGE_SUFFIXES
        ]
        label_members = [
            name
            for name in members
            if name.startswith("labels/") and name.endswith(".txt")
        ]
        images = {dataset_key(name, "images/"): name for name in image_members}
        labels = {dataset_key(name, "labels/"): name for name in label_members}

        instances: Counter[int] = Counter()
        images_per_class: dict[int, set[str]] = defaultdict(set)
        areas: dict[int, list[float]] = defaultdict(list)
        split_images: Counter[str] = Counter()
        split_labels: Counter[str] = Counter()
        invalid_rows: list[dict] = []
        duplicate_rows: list[dict] = []
        empty_labels: list[str] = []

        for key in images:
            split_images[key.split("/", 1)[0]] += 1

        for key, label_name in labels.items():
            split_labels[key.split("/", 1)[0]] += 1
            text = dataset.read(label_name).decode("utf-8-sig").strip()
            if not text:
                empty_labels.append(label_name)
                continue

            seen_rows: set[str] = set()
            for line_number, row in enumerate(text.splitlines(), start=1):
                values = row.split()
                if len(values) != 5:
                    invalid_rows.append(
                        {
                            "file": label_name,
                            "line": line_number,
                            "reason": "expected_5_fields",
                        }
                    )
                    continue
                try:
                    class_id = int(values[0])
                    x_center, y_center, width, height = map(float, values[1:])
                except ValueError:
                    invalid_rows.append(
                        {
                            "file": label_name,
                            "line": line_number,
                            "reason": "non_numeric",
                        }
                    )
                    continue

                if row in seen_rows:
                    duplicate_rows.append(
                        {"file": label_name, "line": line_number, "row": row}
                    )
                seen_rows.add(row)

                coordinates = (x_center, y_center, width, height)
                if (
                    class_id not in class_names
                    or any(value < 0 or value > 1 for value in coordinates)
                    or width <= 0
                    or height <= 0
                ):
                    invalid_rows.append(
                        {
                            "file": label_name,
                            "line": line_number,
                            "reason": "invalid_value",
                        }
                    )
                    continue

                instances[class_id] += 1
                images_per_class[class_id].add(key)
                areas[class_id].append(width * height)

        class_report = []
        for class_id, class_name in class_names.items():
            class_areas = areas[class_id]
            small_count = sum(area < 0.01 for area in class_areas)
            class_report.append(
                {
                    "id": class_id,
                    "name": class_name,
                    "instances": instances[class_id],
                    "images": len(images_per_class[class_id]),
                    "median_relative_box_area": round(statistics.median(class_areas), 6)
                    if class_areas
                    else None,
                    "p10_relative_box_area": round(percentile(class_areas, 0.10), 6)
                    if class_areas
                    else None,
                    "boxes_under_1_percent": small_count,
                    "boxes_under_1_percent_ratio": round(
                        small_count / len(class_areas), 4
                    )
                    if class_areas
                    else None,
                }
            )

        license_text = (
            dataset.read("LICENSE").decode("utf-8-sig") if "LICENSE" in members else ""
        )
        return {
            "archive": str(archive),
            "sha256": sha256(archive),
            "license_file_present": bool(license_text),
            "license_mentions_agpl_3": "AFFERO GENERAL PUBLIC LICENSE" in license_text,
            "image_count": len(images),
            "label_file_count": len(labels),
            "split_image_count": dict(sorted(split_images.items())),
            "split_label_count": dict(sorted(split_labels.items())),
            "orphan_labels": sorted(set(labels) - set(images)),
            "images_without_labels": sorted(set(images) - set(labels)),
            "empty_labels": empty_labels,
            "invalid_rows": invalid_rows,
            "duplicate_rows": duplicate_rows,
            "classes": class_report,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="İncelenecek YOLO ZIP arşivi")
    parser.add_argument("--output", type=Path, help="JSON raporunun yazılacağı dosya")
    args = parser.parse_args()

    if not args.archive.is_file():
        parser.error(f"Arşiv bulunamadı: {args.archive}")

    try:
        report = audit(args.archive)
    except (BadZipFile, UnicodeDecodeError, ValueError) as error:
        parser.error(str(error))

    result = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result + "\n", encoding="utf-8")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
