import hashlib

import pytest
from scripts.train_ppe_model import (
    read_split_provenance,
    sha256,
    validate_resume_checkpoint,
    validate_run_name,
)


def test_sha256_matches_known_content(tmp_path) -> None:
    sample = tmp_path / "sample.bin"
    sample.write_bytes(b"isg-camera")

    assert sha256(sample) == hashlib.sha256(b"isg-camera").hexdigest()


@pytest.mark.parametrize("name", ["b6-smoke", "ppe_v1.0", "run01"])
def test_safe_training_name_is_accepted(name: str) -> None:
    assert validate_run_name(name) == name


@pytest.mark.parametrize("name", ["../outside", "space name", "", "-starts-with-dash"])
def test_unsafe_training_name_is_rejected(name: str) -> None:
    with pytest.raises(ValueError):
        validate_run_name(name)


def test_missing_split_report_is_recorded(tmp_path) -> None:
    data_yaml = tmp_path / "data.yaml"
    data_yaml.write_text("names:\n  0: helmet\n", encoding="utf-8")

    assert read_split_provenance(data_yaml) == {"split_report": None}


def test_resume_checkpoint_must_be_same_runs_last_weights(tmp_path) -> None:
    run_dir = tmp_path / "b6-baseline"
    checkpoint = run_dir / "weights" / "last.pt"

    assert validate_resume_checkpoint(run_dir, checkpoint) == checkpoint.resolve()

    with pytest.raises(ValueError):
        validate_resume_checkpoint(run_dir, run_dir / "weights" / "best.pt")

    with pytest.raises(ValueError):
        validate_resume_checkpoint(run_dir, tmp_path / "other" / "weights" / "last.pt")
