#!/usr/bin/env python3
import argparse
import csv
import json
import subprocess
from pathlib import Path

from PIL import Image


def run_tesseract_tsv(image_path: Path, lang: str = "chi_tra") -> list[dict]:
    completed = subprocess.run(
        ["tesseract", str(image_path), "stdout", "-l", lang, "--psm", "6", "tsv"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0 and not completed.stdout:
        raise RuntimeError(completed.stderr)

    rows = []
    reader = csv.DictReader(completed.stdout.splitlines(), delimiter="\t")
    for row in reader:
        if not row.get("level"):
            continue
        rows.append(row)
    return rows


def int_field(row: dict, field: str) -> int:
    value = row.get(field, "0")
    return int(float(value)) if value else 0


def float_field(row: dict, field: str) -> float:
    value = row.get(field, "-1")
    try:
        return float(value)
    except ValueError:
        return -1.0


def expanded_box(row: dict, image_size: tuple[int, int], padding: int) -> tuple[int, int, int, int]:
    width, height = image_size
    left = max(0, int_field(row, "left") - padding)
    top = max(0, int_field(row, "top") - padding)
    right = min(width, int_field(row, "left") + int_field(row, "width") + padding)
    bottom = min(height, int_field(row, "top") + int_field(row, "height") + padding)
    return left, top, right, bottom


def extract_regions(image_path: Path, output_dir: Path, padding: int) -> list[dict]:
    image = Image.open(image_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = run_tesseract_tsv(image_path)
    regions = []
    words_by_line = {}

    for row in rows:
        if row.get("level") != "5":
            continue
        text = (row.get("text") or "").strip()
        if not text:
            continue
        key = (
            row.get("block_num", "0"),
            row.get("par_num", "0"),
            row.get("line_num", "0"),
        )
        words_by_line.setdefault(key, []).append(text)

    for index, row in enumerate(rows):
        # Tesseract level 4 is a text line. These crops intentionally include
        # surrounding zhuyin marks, even when OCR text is noisy.
        if row.get("level") != "4":
            continue
        if int_field(row, "width") <= 0 or int_field(row, "height") <= 0:
            continue

        box = expanded_box(row, image.size, padding)
        crop = image.crop(box)
        crop_name = f"region_{index:03d}_line_{row.get('line_num', '0')}.png"
        crop_path = output_dir / crop_name
        crop.save(crop_path)
        key = (
            row.get("block_num", "0"),
            row.get("par_num", "0"),
            row.get("line_num", "0"),
        )
        ocr_text = " ".join(words_by_line.get(key, []))

        regions.append(
            {
                "id": crop_path.stem,
                "source_image": str(image_path),
                "crop_path": str(crop_path),
                "bbox": list(box),
                "ocr_text": ocr_text,
                "ocr_confidence": float_field(row, "conf"),
                "block_num": int_field(row, "block_num"),
                "par_num": int_field(row, "par_num"),
                "line_num": int_field(row, "line_num"),
                "status": "visual_region_needs_zhuyin_recognition",
            }
        )

    return regions


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract visual text+zhuyin line regions from a rendered page image."
    )
    parser.add_argument("image", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--padding", type=int, default=24)
    args = parser.parse_args()

    regions = extract_regions(args.image, args.output_dir, args.padding)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps({"source_image": str(args.image), "regions": regions}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(args.json_output)
    print(f"regions={len(regions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
