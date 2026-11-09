"""YOLO ZIP arşivinden grup güvenli ve temiz bir çalışma kopyası üretir.

Ham arşiv değiştirilmez. Birbirine çok benzeyen görüntüler aynı grupta tutulur;
bu gruplar eğitim, doğrulama ve test bölümlerine parçalanmadan dağıtılır. Kaynak
bilgisi bulunan gelecekteki video verileri için ayrıca CSV grup dosyası alınabilir.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import shutil
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SPLIT_RATIOS = {"train": 0.8, "val": 0.1, "test": 0.1}


@dataclass(frozen=True)
class Sample:
    """Bir görüntünün yeniden ayırma için gereken küçük bilgi özeti."""

    image_member: str
    label_member: str
    original_split: str
    filename: str
    class_counts: Counter[int]
    clean_label: str
    perceptual_hash: int
    source_group: str | None = None


class DisjointSet:
    """Benzer görüntüleri tek grupta birleştiren küçük union-find yapısı."""

    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_names(data_yaml: str) -> dict[int, str]:
    """data.yaml içindeki sınıf kimliği ve adlarını ek paket olmadan okur."""
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


def clean_label_rows(
    text: str, class_names: dict[int, str]
) -> tuple[str, Counter[int], int]:
    """Geçerli etiketleri korur, aynı dosyadaki yinelenen satırları bir kez yazar."""
    clean_rows: list[str] = []
    counts: Counter[int] = Counter()
    seen: set[str] = set()
    removed_duplicates = 0

    for line_number, raw_row in enumerate(text.splitlines(), start=1):
        row = " ".join(raw_row.split())
        if not row:
            continue
        values = row.split()
        if len(values) != 5:
            raise ValueError(f"Etiket satırı 5 alan içermiyor: satır {line_number}")
        try:
            class_id = int(values[0])
            x_center, y_center, width, height = map(float, values[1:])
        except ValueError as error:
            raise ValueError(
                f"Etiket satırı sayısal değil: satır {line_number}"
            ) from error
        if (
            class_id not in class_names
            or any(
                value < 0 or value > 1 for value in (x_center, y_center, width, height)
            )
            or width <= 0
            or height <= 0
        ):
            raise ValueError(f"Etiket değeri geçersiz: satır {line_number}")
        if row in seen:
            removed_duplicates += 1
            continue
        seen.add(row)
        clean_rows.append(row)
        counts[class_id] += 1

    clean_text = "\n".join(clean_rows)
    if clean_text:
        clean_text += "\n"
    return clean_text, counts, removed_duplicates


def perceptual_hash(image_bytes: bytes) -> int:
    """Boyut değişimine dayanıklı 64 bit pHash üretir."""
    import cv2
    import numpy as np

    encoded = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError("Görüntü çözülemedi")
    resized = cv2.resize(image, (32, 32), interpolation=cv2.INTER_AREA)
    frequency = cv2.dct(resized.astype(np.float32))[:8, :8]
    values = frequency.flatten()
    median = float(np.median(values[1:]))
    bits = values > median
    result = 0
    for bit in bits:
        result = (result << 1) | int(bit)
    return result


def hamming_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def load_source_groups(path: Path | None) -> dict[str, str]:
    """İsteğe bağlı CSV'den image_member,source_group eşlemesini okur."""
    if path is None:
        return {}
    groups: dict[str, str] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not {"image_member", "source_group"}.issubset(
            reader.fieldnames
        ):
            raise ValueError("Kaynak CSV sütunları image_member,source_group olmalıdır")
        for row_number, row in enumerate(reader, start=2):
            member = (row.get("image_member") or "").strip()
            group = (row.get("source_group") or "").strip()
            if not member or not group:
                raise ValueError(f"Kaynak CSV satırı eksik: {row_number}")
            if member in groups and groups[member] != group:
                raise ValueError(f"Görüntü iki kaynak grubunda: {member}")
            groups[member] = group
    return groups


def build_groups(samples: list[Sample], max_hash_distance: int) -> list[list[int]]:
    """Açık kaynak kimliği veya görsel benzerliği olan örnekleri birleştirir."""
    groups = DisjointSet(len(samples))
    source_first: dict[str, int] = {}
    for index, sample in enumerate(samples):
        if sample.source_group is not None:
            if sample.source_group in source_first:
                groups.union(source_first[sample.source_group], index)
            else:
                source_first[sample.source_group] = index

    for left in range(len(samples)):
        for right in range(left + 1, len(samples)):
            if (
                hamming_distance(
                    samples[left].perceptual_hash, samples[right].perceptual_hash
                )
                <= max_hash_distance
            ):
                groups.union(left, right)

    members: dict[int, list[int]] = defaultdict(list)
    for index in range(len(samples)):
        members[groups.find(index)].append(index)
    return sorted(members.values(), key=lambda item: min(item))


def assign_groups(
    samples: list[Sample], groups: list[list[int]], seed: int
) -> dict[int, str]:
    """Grupları parçalamadan yaklaşık 80/10/10 ve sınıf dengeli dağıtır."""
    total_images = len(samples)
    total_classes: Counter[int] = Counter()
    for sample in samples:
        total_classes.update(sample.class_counts)

    target_images = {
        split: max(1.0, total_images * ratio) for split, ratio in SPLIT_RATIOS.items()
    }
    target_classes = {
        split: {
            class_id: max(1.0, count * ratio)
            for class_id, count in total_classes.items()
        }
        for split, ratio in SPLIT_RATIOS.items()
    }
    assigned_images: Counter[str] = Counter()
    assigned_classes: dict[str, Counter[int]] = {
        split: Counter() for split in SPLIT_RATIOS
    }

    rng = random.Random(seed)
    ordered_groups = list(groups)
    rng.shuffle(ordered_groups)

    def priority(group: list[int]) -> tuple[float, int]:
        group_classes: Counter[int] = Counter()
        for index in group:
            group_classes.update(samples[index].class_counts)
        rarity = sum(
            count / max(1, total_classes[class_id])
            for class_id, count in group_classes.items()
        )
        return rarity, len(group)

    ordered_groups.sort(key=priority, reverse=True)
    assignments: dict[int, str] = {}

    for group in ordered_groups:
        group_classes: Counter[int] = Counter()
        for index in group:
            group_classes.update(samples[index].class_counts)

        def split_score(
            split: str,
            group_size: int = len(group),
            classes: Counter[int] = group_classes,
        ) -> tuple[float, int]:
            image_fill = (assigned_images[split] + group_size) / target_images[split]
            class_fills = [
                (assigned_classes[split][class_id] + count)
                / target_classes[split][class_id]
                for class_id, count in classes.items()
            ]
            class_fill = (
                sum(class_fills) / len(class_fills) if class_fills else image_fill
            )
            return image_fill + class_fill, list(SPLIT_RATIOS).index(split)

        chosen = min(SPLIT_RATIOS, key=split_score)
        assigned_images[chosen] += len(group)
        assigned_classes[chosen].update(group_classes)
        for index in group:
            assignments[index] = chosen

    return assignments


def collect_samples(
    dataset: ZipFile,
    class_names: dict[int, str],
    source_groups: dict[str, str],
) -> tuple[list[Sample], dict[str, int]]:
    members = set(dataset.namelist())
    image_members = sorted(
        name
        for name in members
        if name.startswith("images/")
        and PurePosixPath(name).suffix.lower() in IMAGE_SUFFIXES
    )
    samples: list[Sample] = []
    duplicate_rows_removed = 0

    for image_member in image_members:
        image_path = PurePosixPath(image_member)
        if len(image_path.parts) < 3:
            raise ValueError(
                f"Görüntü yolu images/<split>/... biçiminde değil: {image_member}"
            )
        label_member = str(
            PurePosixPath("labels", *image_path.parts[1:]).with_suffix(".txt")
        )
        if label_member not in members:
            raise ValueError(f"Görüntünün etiketi yok: {image_member}")
        clean_label, class_counts, removed = clean_label_rows(
            dataset.read(label_member).decode("utf-8-sig"), class_names
        )
        duplicate_rows_removed += removed
        image_bytes = dataset.read(image_member)
        samples.append(
            Sample(
                image_member=image_member,
                label_member=label_member,
                original_split=image_path.parts[1],
                filename=image_path.name,
                class_counts=class_counts,
                clean_label=clean_label,
                perceptual_hash=perceptual_hash(image_bytes),
                source_group=source_groups.get(image_member),
            )
        )

    unknown_members = sorted(
        set(source_groups) - {sample.image_member for sample in samples}
    )
    if unknown_members:
        raise ValueError(
            f"Kaynak CSV arşivde olmayan görüntü içeriyor: {unknown_members[0]}"
        )
    return samples, {"duplicate_label_rows_removed": duplicate_rows_removed}


def cross_split_similar_pairs(
    samples: list[Sample], max_hash_distance: int, splits: dict[int, str]
) -> int:
    count = 0
    for left in range(len(samples)):
        for right in range(left + 1, len(samples)):
            if splits[left] == splits[right]:
                continue
            if (
                hamming_distance(
                    samples[left].perceptual_hash, samples[right].perceptual_hash
                )
                <= max_hash_distance
            ):
                count += 1
    return count


def build_report(
    archive: Path,
    samples: list[Sample],
    groups: list[list[int]],
    assignments: dict[int, str],
    max_hash_distance: int,
    seed: int,
    cleanup: dict[str, int],
    source_manifest_used: bool,
) -> dict:
    original_splits = {
        index: sample.original_split for index, sample in enumerate(samples)
    }
    split_images: Counter[str] = Counter(assignments.values())
    split_classes: dict[str, Counter[int]] = {
        split: Counter() for split in SPLIT_RATIOS
    }
    for index, split in assignments.items():
        split_classes[split].update(samples[index].class_counts)

    group_for_index: dict[int, int] = {}
    for group_id, group in enumerate(groups, start=1):
        for index in group:
            group_for_index[index] = group_id

    return {
        "source_archive": str(archive),
        "source_sha256": sha256(archive),
        "method": {
            "split_ratios": SPLIT_RATIOS,
            "seed": seed,
            "perceptual_hash": "64-bit pHash",
            "max_hash_distance": max_hash_distance,
            "source_manifest_used": source_manifest_used,
            "limitation": (
                "Arşiv gerçek çekim/video kaynak kimliği içermiyor. CSV verilmediyse "
                "gruplar yalnız görsel benzerliği gösterir; ortak kaynağı kesin kanıtlamaz."
            ),
        },
        "image_count": len(samples),
        "group_count": len(groups),
        "largest_group_size": max(map(len, groups), default=0),
        "original_split_images": dict(
            sorted(Counter(original_splits.values()).items())
        ),
        "prepared_split_images": dict(sorted(split_images.items())),
        "original_cross_split_similar_pairs": cross_split_similar_pairs(
            samples, max_hash_distance, original_splits
        ),
        "prepared_cross_split_similar_pairs": cross_split_similar_pairs(
            samples, max_hash_distance, assignments
        ),
        "cleanup": cleanup,
        "class_instances_by_split": {
            split: dict(sorted(counts.items()))
            for split, counts in sorted(split_classes.items())
        },
        "samples": [
            {
                "image": sample.image_member,
                "original_split": sample.original_split,
                "prepared_split": assignments[index],
                "group_id": group_for_index[index],
                "source_group": sample.source_group,
                "phash": f"{sample.perceptual_hash:016x}",
            }
            for index, sample in enumerate(samples)
        ],
    }


def write_dataset(
    dataset: ZipFile,
    output_dir: Path,
    samples: list[Sample],
    assignments: dict[int, str],
    class_names: dict[int, str],
    report: dict,
) -> None:
    if output_dir.exists():
        raise ValueError(f"Çıktı klasörü zaten var; üzerine yazılmadı: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}-", dir=output_dir.parent)
    )
    try:
        for split in SPLIT_RATIOS:
            (temporary / "images" / split).mkdir(parents=True)
            (temporary / "labels" / split).mkdir(parents=True)

        used_names: set[str] = set()
        for index, sample in enumerate(samples):
            if sample.filename in used_names:
                raise ValueError(
                    f"Aynı dosya adı birden fazla görüntüde var: {sample.filename}"
                )
            used_names.add(sample.filename)
            split = assignments[index]
            image_target = temporary / "images" / split / sample.filename
            label_target = (
                temporary
                / "labels"
                / split
                / PurePosixPath(sample.filename).with_suffix(".txt").name
            )
            image_target.write_bytes(dataset.read(sample.image_member))
            label_target.write_text(sample.clean_label, encoding="utf-8")

        dataset_path = json.dumps(output_dir.resolve().as_posix(), ensure_ascii=False)
        yaml_lines = [
            f"path: {dataset_path}",
            "train: images/train",
            "val: images/val",
            "test: images/test",
            "",
            "names:",
        ]
        yaml_lines.extend(
            f"  {class_id}: {name}" for class_id, name in class_names.items()
        )
        (temporary / "data.yaml").write_text(
            "\n".join(yaml_lines) + "\n", encoding="utf-8"
        )
        if "LICENSE" in dataset.namelist():
            (temporary / "LICENSE").write_bytes(dataset.read("LICENSE"))
        (temporary / "split-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        temporary.replace(output_dir)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def prepare(args: argparse.Namespace) -> dict:
    source_groups = load_source_groups(args.source_groups)
    with ZipFile(args.archive) as dataset:
        if "data.yaml" not in dataset.namelist():
            raise ValueError("ZIP kökünde data.yaml bulunamadı")
        class_names = parse_names(dataset.read("data.yaml").decode("utf-8-sig"))
        samples, cleanup = collect_samples(dataset, class_names, source_groups)
        groups = build_groups(samples, args.max_hash_distance)
        assignments = assign_groups(samples, groups, args.seed)
        report = build_report(
            archive=args.archive,
            samples=samples,
            groups=groups,
            assignments=assignments,
            max_hash_distance=args.max_hash_distance,
            seed=args.seed,
            cleanup=cleanup,
            source_manifest_used=bool(args.source_groups),
        )
        if report["prepared_cross_split_similar_pairs"] != 0:
            raise RuntimeError("Benzer görüntü grubu bölümler arasında parçalandı")
        write_dataset(
            dataset, args.output_dir, samples, assignments, class_names, report
        )
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Kaynak YOLO ZIP arşivi")
    parser.add_argument("output_dir", type=Path, help="Yeni çalışma veri seti klasörü")
    parser.add_argument(
        "--source-groups",
        type=Path,
        help="İsteğe bağlı image_member,source_group sütunlu UTF-8 CSV",
    )
    parser.add_argument(
        "--seed", type=int, default=20261109, help="Tekrarlanabilir ayırma tohumu"
    )
    parser.add_argument(
        "--max-hash-distance",
        type=int,
        default=4,
        help="Benzer kabul edilen pHash Hamming uzaklığı (varsayılan: 4)",
    )
    args = parser.parse_args()

    if not args.archive.is_file():
        parser.error(f"Arşiv bulunamadı: {args.archive}")
    if args.source_groups is not None and not args.source_groups.is_file():
        parser.error(f"Kaynak grup CSV dosyası bulunamadı: {args.source_groups}")
    if not 0 <= args.max_hash_distance <= 64:
        parser.error("max-hash-distance 0 ile 64 arasında olmalıdır")

    try:
        report = prepare(args)
    except (BadZipFile, OSError, RuntimeError, UnicodeDecodeError, ValueError) as error:
        parser.error(str(error))
    summary = {key: value for key, value in report.items() if key != "samples"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
