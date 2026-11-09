from collections import Counter

import pytest
from scripts.prepare_yolo_dataset import (
    Sample,
    assign_groups,
    build_groups,
    clean_label_rows,
)


def make_sample(
    name: str,
    perceptual_hash: int,
    class_id: int = 0,
    source_group: str | None = None,
) -> Sample:
    return Sample(
        image_member=f"images/train/{name}.jpg",
        label_member=f"labels/train/{name}.txt",
        original_split="train",
        filename=f"{name}.jpg",
        class_counts=Counter({class_id: 1}),
        clean_label=f"{class_id} 0.5 0.5 0.2 0.2\n",
        perceptual_hash=perceptual_hash,
        source_group=source_group,
    )


def test_duplicate_label_row_is_written_once() -> None:
    text = "0 0.5 0.5 0.2 0.2\n0 0.5 0.5 0.2 0.2\n1 0.4 0.4 0.1 0.1\n"

    clean, counts, removed = clean_label_rows(text, {0: "helmet", 1: "vest"})

    assert clean.count("0 0.5 0.5 0.2 0.2") == 1
    assert counts == Counter({0: 1, 1: 1})
    assert removed == 1


def test_invalid_label_value_is_rejected() -> None:
    with pytest.raises(ValueError, match="geçersiz"):
        clean_label_rows("0 1.2 0.5 0.2 0.2\n", {0: "helmet"})


def test_visually_similar_samples_stay_in_one_group() -> None:
    samples = [
        make_sample("a", 0b0000),
        make_sample("b", 0b0001),
        make_sample("c", 0b1111),
    ]

    groups = build_groups(samples, max_hash_distance=1)

    assert groups == [[0, 1], [2]]


def test_same_video_source_stays_in_one_group_even_if_frames_look_different() -> None:
    samples = [
        make_sample("a", 0x0000, source_group="camera-1-session-1"),
        make_sample("b", 0xFFFF, source_group="camera-1-session-1"),
        make_sample("c", 0x00FF, source_group="camera-2-session-1"),
    ]

    groups = build_groups(samples, max_hash_distance=0)

    assert groups == [[0, 1], [2]]


def test_assignment_is_deterministic_and_never_splits_group() -> None:
    samples = [make_sample(str(index), index * 17, index % 2) for index in range(30)]
    groups = [[0, 1], *[[index] for index in range(2, 30)]]

    first = assign_groups(samples, groups, seed=42)
    second = assign_groups(samples, groups, seed=42)

    assert first == second
    assert first[0] == first[1]
    assert set(first.values()) == {"train", "val", "test"}
