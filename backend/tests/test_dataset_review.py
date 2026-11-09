import json

import pytest
from scripts.create_dataset_review import load_review_rows, natural_image_key


def test_natural_image_key_orders_numbered_images() -> None:
    names = ["image10.jpg", "image2.jpg", "image1.jpg"]

    assert sorted(names, key=natural_image_key) == [
        "image1.jpg",
        "image2.jpg",
        "image10.jpg",
    ]


def test_load_review_rows_resolves_prepared_split(tmp_path) -> None:
    (tmp_path / "images" / "val").mkdir(parents=True)
    (tmp_path / "labels" / "val").mkdir(parents=True)
    (tmp_path / "images" / "val" / "image2.jpg").write_bytes(b"image")
    (tmp_path / "labels" / "val" / "image2.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    report = {
        "samples": [
            {
                "image": "images/train/image2.jpg",
                "prepared_split": "val",
                "group_id": 7,
            }
        ]
    }
    (tmp_path / "split-report.json").write_text(json.dumps(report), encoding="utf-8")

    assert load_review_rows(tmp_path) == [
        {
            "image": "images/val/image2.jpg",
            "label": "labels/val/image2.txt",
            "filename": "image2.jpg",
            "group_id": 7,
            "split": "val",
            "status": "unreviewed",
            "reason": "",
        }
    ]


def test_load_review_rows_rejects_missing_label(tmp_path) -> None:
    (tmp_path / "images" / "train").mkdir(parents=True)
    (tmp_path / "images" / "train" / "image1.jpg").write_bytes(b"image")
    (tmp_path / "split-report.json").write_text(
        json.dumps(
            {
                "samples": [
                    {
                        "image": "images/train/image1.jpg",
                        "prepared_split": "train",
                        "group_id": 1,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_review_rows(tmp_path)
