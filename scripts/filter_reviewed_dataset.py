"""Görsel inceleme kararına göre hazırlanmış YOLO veri setini filtreler.

Kaynak klasör değiştirilmez. Karar dosyasındaki her görüntü numarası tam olarak
bir kuralla eşleşmek zorundadır; benzerlik grubunun yalnız bir kısmını tutmaya
izin verilmez.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

IMAGE_NAME_PATTERN = re.compile(
    r"^image(\d+)\.(?:jpg|jpeg|png|bmp|webp)$", re.IGNORECASE
)
VALID_ACTIONS = {"include", "exclude"}


def image_number(filename: str) -> int:
    """Construction-PPE dosya adından sayısal kimliği çıkarır."""
    match = IMAGE_NAME_PATTERN.fullmatch(filename)
    if not match:
        raise ValueError(f"Beklenmeyen görüntü adı: {filename}")
    return int(match.group(1))


def select_rule(number: int, rules: list[dict]) -> dict:
    """Bir görüntünün çakışmayan tek inceleme kuralını bulur."""
    matches = [
        rule
        for rule in rules
        if int(rule["first_image_number"]) <= number <= int(rule["last_image_number"])
    ]
    if len(matches) != 1:
        raise ValueError(
            f"image{number} için tam bir inceleme kuralı bekleniyordu; "
            f"eşleşme sayısı: {len(matches)}"
        )
    rule = matches[0]
    if rule.get("action") not in VALID_ACTIONS:
        raise ValueError(f"Geçersiz inceleme kararı: {rule.get('action')}")
    return rule


def count_label_classes(label_path: Path) -> Counter[int]:
    """Bir YOLO etiket dosyasındaki sınıf örneklerini sayar."""
    counts: Counter[int] = Counter()
    for line_number, row in enumerate(
        label_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        values = row.split()
        if len(values) != 5:
            raise ValueError(f"Geçersiz etiket satırı: {label_path}:{line_number}")
        counts[int(values[0])] += 1
    return counts


def transform_label(
    label_path: Path, class_policy: dict
) -> tuple[str, Counter[int], Counter[int]]:
    """Tutulan sınıfları yeniden numaralandırır, belirsiz sınıfları çıkarır."""
    keep = class_policy.get("keep")
    drop = class_policy.get("drop")
    if not isinstance(keep, dict) or not isinstance(drop, dict):
        raise TypeError("İnceleme kararında keep/drop sınıf politikası eksik")
    output_rows: list[str] = []
    kept_counts: Counter[int] = Counter()
    dropped_counts: Counter[int] = Counter()
    for line_number, row in enumerate(
        label_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        values = row.split()
        if len(values) != 5:
            raise ValueError(f"Geçersiz etiket satırı: {label_path}:{line_number}")
        old_id = int(values[0])
        old_key = str(old_id)
        if old_key in keep:
            new_id = int(keep[old_key]["new_id"])
            output_rows.append(" ".join([str(new_id), *values[1:]]))
            kept_counts[new_id] += 1
        elif old_key in drop:
            dropped_counts[old_id] += 1
        else:
            raise ValueError(f"Sınıf politikasında bulunmayan kimlik: {old_id}")
    text = "\n".join(output_rows)
    return (text + "\n" if text else ""), kept_counts, dropped_counts


def build_filter_plan(source_dir: Path, review: dict) -> tuple[list[dict], dict]:
    """B5 raporundaki tüm örnekler için tutma/çıkarma planı ve özet üretir."""
    split_report_path = source_dir / "split-report.json"
    if not split_report_path.is_file():
        raise ValueError(f"B5 ayırma raporu bulunamadı: {split_report_path}")
    split_report = json.loads(split_report_path.read_text(encoding="utf-8"))
    expected_hash = review.get("source_archive_sha256")
    if split_report.get("source_sha256") != expected_hash:
        raise ValueError("İnceleme kararı bu kaynak arşive ait değil")
    rules = review.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError("İnceleme kararında kural yok")

    plan: list[dict] = []
    group_actions: dict[int, set[str]] = defaultdict(set)
    action_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    split_counts: dict[str, Counter[str]] = defaultdict(Counter)
    class_counts: dict[str, Counter[int]] = defaultdict(Counter)
    dropped_class_counts: Counter[int] = Counter()
    excluded_class_counts: Counter[int] = Counter()
    class_policy = review.get("class_policy")
    if not isinstance(class_policy, dict):
        raise TypeError("İnceleme kararında class_policy yok")

    for sample in split_report.get("samples", []):
        filename = Path(str(sample["image"])).name
        split = str(sample["prepared_split"])
        rule = select_rule(image_number(filename), rules)
        action = str(rule["action"])
        category = str(rule.get("category", "unspecified"))
        group_id = int(sample["group_id"])
        image_path = source_dir / "images" / split / filename
        label_path = source_dir / "labels" / split / Path(filename).with_suffix(".txt")
        if not image_path.is_file() or not label_path.is_file():
            raise ValueError(f"Kaynak görüntü veya etiketi eksik: {filename}")
        group_actions[group_id].add(action)
        action_counts[action] += 1
        category_counts[category] += 1
        split_counts[action][split] += 1
        clean_label = None
        if action == "include":
            clean_label, kept, dropped = transform_label(label_path, class_policy)
            class_counts[split].update(kept)
            dropped_class_counts.update(dropped)
        else:
            excluded_class_counts.update(count_label_classes(label_path))
        plan.append(
            {
                "filename": filename,
                "split": split,
                "group_id": group_id,
                "action": action,
                "category": category,
                "image_path": image_path,
                "label_path": label_path,
                "clean_label": clean_label,
            }
        )

    mixed_groups = sorted(
        group_id for group_id, actions in group_actions.items() if len(actions) != 1
    )
    if mixed_groups:
        raise ValueError(
            "Benzerlik grubunun yalnız bir kısmı dışlanamaz; ilk karma grup: "
            f"{mixed_groups[0]}"
        )
    if not plan:
        raise ValueError("B5 ayırma raporunda örnek yok")
    for split in ("train", "val", "test"):
        if split_counts["include"][split] == 0:
            raise ValueError(f"Filtre sonrası {split} bölümü boş")

    summary = {
        "source_image_count": len(plan),
        "included_image_count": action_counts["include"],
        "excluded_image_count": action_counts["exclude"],
        "categories": dict(sorted(category_counts.items())),
        "included_images_by_split": dict(sorted(split_counts["include"].items())),
        "excluded_images_by_split": dict(sorted(split_counts["exclude"].items())),
        "included_class_instances_by_split": {
            split: {str(key): value for key, value in sorted(counts.items())}
            for split, counts in sorted(class_counts.items())
        },
        "dropped_class_instances": {
            str(key): value for key, value in sorted(dropped_class_counts.items())
        },
        "excluded_class_instances": {
            str(key): value for key, value in sorted(excluded_class_counts.items())
        },
        "partial_similarity_groups": 0,
    }
    return plan, summary


def write_filtered_dataset(
    source_dir: Path,
    output_dir: Path,
    review_path: Path,
    plan: list[dict],
    summary: dict,
) -> None:
    """Tutulan örnekleri yeni klasöre güvenli biçimde kopyalar."""
    if output_dir.exists():
        raise ValueError(f"Çıktı klasörü zaten var; üzerine yazılmadı: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}-", dir=output_dir.parent)
    )
    try:
        for split in ("train", "val", "test"):
            (temporary / "images" / split).mkdir(parents=True)
            (temporary / "labels" / split).mkdir(parents=True)
        for item in plan:
            if item["action"] != "include":
                continue
            split = item["split"]
            shutil.copy2(item["image_path"], temporary / "images" / split)
            label_target = temporary / "labels" / split / item["label_path"].name
            label_target.write_text(item["clean_label"], encoding="utf-8")

        review = json.loads(review_path.read_text(encoding="utf-8"))
        keep = review["class_policy"]["keep"]
        ordered_names = sorted(
            (int(value["new_id"]), str(value["name"])) for value in keep.values()
        )
        if [class_id for class_id, _ in ordered_names] != list(
            range(len(ordered_names))
        ):
            raise ValueError(
                "Yeni sınıf kimlikleri sıfırdan başlayan kesintisiz sıra olmalı"
            )
        yaml_lines = [
            f'path: "{output_dir.resolve().as_posix()}"',
            "train: images/train",
            "val: images/val",
            "test: images/test",
            "",
            "names:",
            *(f"  {class_id}: {name}" for class_id, name in ordered_names),
        ]
        (temporary / "data.yaml").write_text(
            "\n".join(yaml_lines) + "\n", encoding="utf-8"
        )
        for filename in ("LICENSE", "split-report.json"):
            source = source_dir / filename
            if source.is_file():
                shutil.copy2(source, temporary / filename)
        shutil.copy2(review_path, temporary / "scene-review.json")
        report = {
            **summary,
            "source_dataset": str(source_dir),
            "review_file": str(review_path),
            "output_dataset": str(output_dir),
            "warning": (
                "Sahne filtresi kutu etiketlerinin doğruluğunu kanıtlamaz. "
                "Yeni model ayrı bir temel deney olarak eğitilmelidir."
            ),
        }
        (temporary / "filter-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(output_dir)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def filter_dataset(args: argparse.Namespace) -> dict:
    source_dir = args.source_dir.resolve()
    review_path = args.review.resolve()
    output_dir = args.output_dir.resolve()
    if not review_path.is_file():
        raise ValueError(f"İnceleme kararı bulunamadı: {review_path}")
    review = json.loads(review_path.read_text(encoding="utf-8"))
    plan, summary = build_filter_plan(source_dir, review)
    write_filtered_dataset(source_dir, output_dir, review_path, plan, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_dir", type=Path, help="B5 hazırlanmış veri klasörü")
    parser.add_argument("review", type=Path, help="Sahne inceleme karar JSON dosyası")
    parser.add_argument("output_dir", type=Path, help="Yeni filtrelenmiş veri klasörü")
    args = parser.parse_args()
    try:
        result = filter_dataset(args)
    except (OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
