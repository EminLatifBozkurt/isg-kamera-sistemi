"""Hazırlanmış veri seti için görsel sahne inceleme paketini oluşturur.

Araç görüntüleri değiştirmez. Küçük önizlemeleri sayfalara dizer ve her görüntüyü
grup kimliğiyle birlikte JSON listeye yazar. İnceleme çıktıları `data/` altında
kalır; model eğitiminde doğrudan kullanılmaz.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REVIEW_STATUSES = {
    "unreviewed",
    "workplace",
    "staged_ppe",
    "unrelated",
    "ambiguous",
}


def natural_image_key(name: str) -> tuple:
    """image9 adını image10'dan önce sıralayan doğal dosya anahtarı üretir."""
    return tuple(
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", name)
    )


def load_review_rows(dataset_dir: Path) -> list[dict]:
    """B5 ayırma raporunu gerçek hazırlanmış görüntü yollarıyla birleştirir."""
    report_path = dataset_dir / "split-report.json"
    if not report_path.is_file():
        raise ValueError(f"Ayırma raporu bulunamadı: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    samples = report.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("Ayırma raporunda görüntü listesi yok")

    rows: list[dict] = []
    seen_paths: set[str] = set()
    for sample in samples:
        original_name = Path(str(sample["image"])).name
        prepared_split = str(sample["prepared_split"])
        relative_image = Path("images") / prepared_split / original_name
        image_path = dataset_dir / relative_image
        label_path = (
            dataset_dir
            / "labels"
            / prepared_split
            / Path(original_name).with_suffix(".txt")
        )
        if not image_path.is_file() or not label_path.is_file():
            raise ValueError(f"Görüntü veya etiketi eksik: {relative_image.as_posix()}")
        normalized = relative_image.as_posix()
        if normalized in seen_paths:
            raise ValueError(f"Görüntü iki kez listelenmiş: {normalized}")
        seen_paths.add(normalized)
        rows.append(
            {
                "image": normalized,
                "label": label_path.relative_to(dataset_dir).as_posix(),
                "filename": original_name,
                "group_id": int(sample["group_id"]),
                "split": prepared_split,
                "status": "unreviewed",
                "reason": "",
            }
        )
    return sorted(rows, key=lambda row: natural_image_key(row["filename"]))


def build_contact_sheets(
    dataset_dir: Path,
    output_dir: Path,
    rows: list[dict],
    columns: int,
    rows_per_sheet: int,
) -> list[str]:
    """Tüm görüntüleri dosya adı görünen sabit boyutlu inceleme sayfalarına dizer."""
    from PIL import Image, ImageDraw, ImageFont, ImageOps

    tile_width = 180
    image_height = 130
    label_height = 28
    tile_height = image_height + label_height
    page_size = columns * rows_per_sheet
    font = ImageFont.load_default(size=14)
    sheet_dir = output_dir / "sheets"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    sheet_names: list[str] = []

    for start in range(0, len(rows), page_size):
        page_rows = rows[start : start + page_size]
        sheet_number = start // page_size + 1
        sheet = Image.new(
            "RGB", (columns * tile_width, rows_per_sheet * tile_height), "#202124"
        )
        draw = ImageDraw.Draw(sheet)
        for position, row in enumerate(page_rows):
            x = (position % columns) * tile_width
            y = (position // columns) * tile_height
            with Image.open(dataset_dir / row["image"]) as source:
                preview = ImageOps.contain(
                    source.convert("RGB"), (tile_width - 4, image_height - 4)
                )
            image_x = x + (tile_width - preview.width) // 2
            image_y = y + (image_height - preview.height) // 2
            sheet.paste(preview, (image_x, image_y))
            draw.rectangle(
                (x, y, x + tile_width - 1, y + tile_height - 1),
                outline="#5f6368",
                width=1,
            )
            caption = f"{row['filename']}  g{row['group_id']}  {row['split']}"
            draw.text((x + 4, y + image_height + 5), caption, fill="white", font=font)

        sheet_name = f"sheet-{sheet_number:03d}.jpg"
        sheet.save(sheet_dir / sheet_name, quality=90, optimize=True)
        sheet_names.append(f"sheets/{sheet_name}")
    return sheet_names


def create_review(args: argparse.Namespace) -> dict:
    """Manifest ve görsel sayfaları yeni bir çıktı klasöründe oluşturur."""
    dataset_dir = args.dataset_dir.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f"İnceleme klasörü zaten var; üzerine yazılmadı: {output_dir}")
    output_dir.mkdir(parents=True)
    rows = load_review_rows(dataset_dir)
    try:
        sheets = build_contact_sheets(
            dataset_dir, output_dir, rows, args.columns, args.rows_per_sheet
        )
        manifest = {
            "dataset": str(dataset_dir),
            "image_count": len(rows),
            "allowed_statuses": sorted(REVIEW_STATUSES),
            "instructions": (
                "Aynı görsel grubundaki örnekler birlikte değerlendirilmelidir. "
                "İş yeri dışı sahneler unrelated, kararsız örnekler ambiguous kalır."
            ),
            "sheets": sheets,
            "samples": rows,
        }
        (output_dir / "review-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return {"image_count": len(rows), "sheet_count": len(sheets)}
    except Exception:
        # Yarım çıktı eğitim verisi sanılmasın; yalnız oluşturduğumuz klasörü temizleriz.
        import shutil

        shutil.rmtree(output_dir, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", type=Path, help="B5 hazırlanmış veri klasörü")
    parser.add_argument("output_dir", type=Path, help="Git dışı inceleme klasörü")
    parser.add_argument("--columns", type=int, default=8)
    parser.add_argument("--rows-per-sheet", type=int, default=8)
    args = parser.parse_args()
    if args.columns <= 0 or args.rows_per_sheet <= 0:
        parser.error("columns ve rows-per-sheet pozitif olmalıdır")
    try:
        result = create_review(args)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
