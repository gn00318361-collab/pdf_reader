#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps
from PIL import ImageDraw


SOURCE_IMAGE = Path("artifacts/page22_regions/target_chengwei.png")
RAW_DIR = Path("dataset/zhuyin_crops/raw")
PROCESSED_DIR = Path("dataset/zhuyin_crops/processed")
LABELS_PATH = Path("dataset/labels/zhuyin_labels.csv")
METADATA_PATH = Path("dataset/metadata/crops.json")
CONTACT_SHEET_PATH = Path("dataset/zhuyin_crops/contact_sheet_page22.png")

# Coordinates are measured on artifacts/page22_regions/target_chengwei.png.
# These crops intentionally focus on the zhuyin printed beside each character,
# not on the large Chinese character itself.
CROPS = [
    {
        "crop_id": "p22_cheng_001",
        "page": 22,
        "char": "成",
        "word_context": "成為",
        "text_bbox": [935, 260, 1190, 575],
        "zhuyin_bbox": [1180, 280, 1365, 590],
        "expected_zhuyin": "ㄔㄥˊ",
        "known_printed_issue": False,
        "notes": "Manual reviewer should confirm printed zhuyin.",
    },
    {
        "crop_id": "p22_wei_001",
        "page": 22,
        "char": "為",
        "word_context": "成為",
        "text_bbox": [1350, 260, 1605, 575],
        "zhuyin_bbox": [1545, 280, 1745, 590],
        "expected_zhuyin": "ㄨㄟˊ",
        "known_printed_issue": True,
        "notes": "Known target: printed zhuyin/tone for 為 is wrong. Fill printed_zhuyin from crop.",
    },
    {
        "crop_id": "p22_wen_001",
        "page": 22,
        "char": "溫",
        "word_context": "溫暖",
        "text_bbox": [1720, 260, 1995, 575],
        "zhuyin_bbox": [1955, 280, 2115, 590],
        "expected_zhuyin": "ㄨㄣ",
        "known_printed_issue": False,
        "notes": "Manual reviewer should confirm printed zhuyin.",
    },
    {
        "crop_id": "p22_nuan_001",
        "page": 22,
        "char": "暖",
        "word_context": "溫暖",
        "text_bbox": [2050, 260, 2280, 575],
        "zhuyin_bbox": [2185, 280, 2280, 610],
        "expected_zhuyin": "ㄋㄨㄢˇ",
        "known_printed_issue": False,
        "notes": "Right edge is clipped in target crop; use as a weak sample or replace with a wider crop later.",
    },
]


CSV_FIELDS = [
    "crop_id",
    "page",
    "char",
    "word_context",
    "crop_path",
    "processed_crop_path",
    "crop_bbox",
    "text_bbox",
    "zhuyin_bbox",
    "render_scale",
    "expected_zhuyin",
    "printed_zhuyin",
    "label_status",
    "status",
    "known_printed_issue",
    "notes",
]


def process_crop(crop: Image.Image) -> Image.Image:
    enlarged = crop.resize((crop.width * 4, crop.height * 4), Image.Resampling.LANCZOS)
    gray = ImageOps.grayscale(enlarged)
    return gray.filter(ImageFilter.SHARPEN).filter(ImageFilter.SHARPEN)


def union_box(boxes: list[list[int]], padding: int, image_size: tuple[int, int]) -> list[int]:
    width, height = image_size
    left = max(0, min(box[0] for box in boxes) - padding)
    top = max(0, min(box[1] for box in boxes) - padding)
    right = min(width, max(box[2] for box in boxes) + padding)
    bottom = min(height, max(box[3] for box in boxes) + padding)
    return [left, top, right, bottom]


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_contact_sheet(rows: list[dict], output_path: Path) -> None:
    thumbs = []
    for row in rows:
        crop = Image.open(row["crop_path"]).convert("RGB")
        crop.thumbnail((220, 220), Image.Resampling.LANCZOS)
        thumbs.append((row, crop.copy()))

    cell_w = 360
    cell_h = 300
    sheet = Image.new("RGB", (cell_w * 2, cell_h * 2), "white")
    draw = ImageDraw.Draw(sheet)

    for index, (row, thumb) in enumerate(thumbs):
        col = index % 2
        line = index // 2
        x = col * cell_w
        y = line * cell_h
        draw.text((x + 16, y + 12), row["crop_id"], fill="black")
        draw.text(
            (x + 16, y + 36),
            f"{row['word_context']} / {row['char']} / expected {row['expected_zhuyin']}",
            fill="black",
        )
        sheet.paste(thumb, (x + 16, y + 70))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare initial page 22 zhuyin crop dataset.")
    parser.add_argument("--source-image", type=Path, default=SOURCE_IMAGE)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--labels", type=Path, default=LABELS_PATH)
    parser.add_argument("--metadata", type=Path, default=METADATA_PATH)
    args = parser.parse_args()

    source = Image.open(args.source_image)
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    args.processed_dir.mkdir(parents=True, exist_ok=True)
    args.metadata.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    metadata_crops = []
    for item in CROPS:
        crop_bbox = union_box(
            [item["text_bbox"], item["zhuyin_bbox"]],
            padding=24,
            image_size=source.size,
        )
        raw_crop = source.crop(tuple(crop_bbox))
        raw_path = args.raw_dir / f"{item['crop_id']}.png"
        raw_crop.save(raw_path)

        processed = process_crop(raw_crop)
        processed_path = args.processed_dir / f"{item['crop_id']}_processed.png"
        processed.save(processed_path)

        row = {
            "crop_id": item["crop_id"],
            "page": item["page"],
            "char": item["char"],
            "word_context": item["word_context"],
            "crop_path": str(raw_path),
            "processed_crop_path": str(processed_path),
            "crop_bbox": json.dumps(crop_bbox, ensure_ascii=False),
            "text_bbox": json.dumps(item["text_bbox"], ensure_ascii=False),
            "zhuyin_bbox": json.dumps(item["zhuyin_bbox"], ensure_ascii=False),
            "render_scale": 3,
            "expected_zhuyin": item["expected_zhuyin"],
            "printed_zhuyin": "",
            "label_status": "unlabeled",
            "status": "unknown",
            "known_printed_issue": str(item["known_printed_issue"]).lower(),
            "notes": item["notes"],
        }
        rows.append(row)
        metadata_crops.append(row)

    write_csv(rows, args.labels)
    write_contact_sheet(rows, CONTACT_SHEET_PATH)
    args.metadata.write_text(
        json.dumps(
            {
                "source_image": str(args.source_image),
                "task": "Read printed zhuyin from crops, then compare with expected_zhuyin.",
                "label_policy": {
                    "printed_zhuyin": "PDF actual printed zhuyin. Fill manually.",
                    "expected_zhuyin": "Standard pronunciation. Do not use as OCR training target.",
                    "label_status": "unlabeled | labeled | uncertain",
                    "status": "unknown | correct | error | uncertain",
                },
                "crops": metadata_crops,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(args.labels)
    print(args.metadata)
    print(CONTACT_SHEET_PATH)
    print(f"crops={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
