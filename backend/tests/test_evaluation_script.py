import pytest
from scripts.evaluate_ppe_model import (
    calculate_runtime,
    count_images,
    find_weak_classes,
    to_json_value,
)


def test_count_images_ignores_non_images(tmp_path) -> None:
    (tmp_path / "camera-a").mkdir()
    (tmp_path / "camera-a" / "frame.jpg").write_bytes(b"image")
    (tmp_path / "frame.PNG").write_bytes(b"image")
    (tmp_path / "labels.txt").write_text("not an image", encoding="utf-8")

    assert count_images(tmp_path) == 2


def test_count_images_rejects_missing_directory(tmp_path) -> None:
    with pytest.raises(ValueError):
        count_images(tmp_path / "missing")


def test_find_weak_classes_uses_instances_and_map50() -> None:
    rows = [
        {"Class": "helmet", "Instances": 10, "mAP50": 0.85},
        {"Class": "no_helmet", "Instances": 8, "mAP50": 0.12},
        {"Class": "unused", "Instances": 0, "mAP50": 0.0},
    ]

    assert find_weak_classes(rows, 0.30) == ["no_helmet"]


def test_calculate_runtime_reports_pipeline_and_fps() -> None:
    result = calculate_runtime(
        {"preprocess": 1.0, "inference": 8.0, "loss": 2.0, "postprocess": 1.0}
    )

    assert result["pipeline_ms_per_image"] == 10.0
    assert result["approx_pipeline_fps"] == 100.0


def test_to_json_value_converts_library_scalars() -> None:
    class LibraryInteger:
        def item(self):
            return 12

    assert to_json_value({"count": LibraryInteger()}) == {"count": 12}
