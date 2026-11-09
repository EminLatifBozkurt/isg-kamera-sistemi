import pytest
from scripts.filter_reviewed_dataset import image_number, select_rule, transform_label


def test_image_number_accepts_supported_names() -> None:
    assert image_number("image1117.jpg") == 1117
    assert image_number("image4.JPEG") == 4


def test_image_number_rejects_unexpected_name() -> None:
    with pytest.raises(ValueError):
        image_number("worker.jpg")


def test_select_rule_requires_exactly_one_match() -> None:
    rules = [
        {"first_image_number": 1, "last_image_number": 10, "action": "include"},
        {"first_image_number": 11, "last_image_number": 20, "action": "exclude"},
    ]

    assert select_rule(11, rules)["action"] == "exclude"

    with pytest.raises(ValueError):
        select_rule(21, rules)


def test_select_rule_rejects_overlap() -> None:
    rules = [
        {"first_image_number": 1, "last_image_number": 10, "action": "include"},
        {"first_image_number": 10, "last_image_number": 20, "action": "exclude"},
    ]

    with pytest.raises(ValueError):
        select_rule(10, rules)


def test_transform_label_remaps_and_drops_classes(tmp_path) -> None:
    label = tmp_path / "image1.txt"
    label.write_text(
        "0 0.5 0.5 0.2 0.2\n5 0.5 0.5 0.3 0.3\n6 0.5 0.5 0.8 0.8\n",
        encoding="utf-8",
    )
    policy = {
        "keep": {
            "0": {"new_id": 0, "name": "helmet"},
            "6": {"new_id": 1, "name": "Person"},
        },
        "drop": {"5": "ambiguous"},
    }

    text, kept, dropped = transform_label(label, policy)

    assert text == "0 0.5 0.5 0.2 0.2\n1 0.5 0.5 0.8 0.8\n"
    assert kept == {0: 1, 1: 1}
    assert dropped == {5: 1}
