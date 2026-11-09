"""Ultralytics'in arka planda yazı tipi indirmesini engelleyen yardımcılar."""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterable
from pathlib import Path


def default_font_candidates() -> list[Path]:
    """İşletim sistemlerinde sık bulunan yerel TrueType yazı tiplerini döndürür."""
    candidates: list[Path] = []
    windows_dir = os.environ.get("WINDIR")
    if windows_dir:
        candidates.append(Path(windows_dir) / "Fonts" / "arial.ttf")
    candidates.extend(
        [
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        ]
    )
    return candidates


def ensure_local_ultralytics_font(
    config_dir: Path, font_candidates: Iterable[Path] | None = None
) -> Path:
    """Ultralytics için yerel font hazırlar; ağdan indirmeye izin vermez."""
    target = config_dir.resolve() / "Ultralytics" / "Arial.ttf"
    if target.is_file():
        return target

    candidates = list(font_candidates or default_font_candidates())
    source = next((path for path in candidates if path.is_file()), None)
    if source is None:
        checked = ", ".join(str(path) for path in candidates)
        raise RuntimeError(
            "Yerel yazı tipi bulunamadı; gizli indirme yapılmadı. "
            f"Kontrol edilen yollar: {checked}"
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target
