from pathlib import Path

import pytest
from scripts.offline_ultralytics import ensure_local_ultralytics_font


def test_local_font_is_copied_without_network(tmp_path) -> None:
    source = tmp_path / "system-font.ttf"
    source.write_bytes(b"local-font")

    result = ensure_local_ultralytics_font(tmp_path / "config", font_candidates=[source])

    assert result == (tmp_path / "config" / "Ultralytics" / "Arial.ttf").resolve()
    assert result.read_bytes() == b"local-font"


def test_existing_font_is_kept(tmp_path) -> None:
    target = tmp_path / "config" / "Ultralytics" / "Arial.ttf"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"existing")

    result = ensure_local_ultralytics_font(
        tmp_path / "config", font_candidates=[Path("missing.ttf")]
    )

    assert result.read_bytes() == b"existing"


def test_missing_local_font_stops_instead_of_downloading(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="gizli indirme yapılmadı"):
        ensure_local_ultralytics_font(
            tmp_path / "config", font_candidates=[tmp_path / "missing.ttf"]
        )
