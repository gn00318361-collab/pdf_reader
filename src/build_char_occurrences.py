from __future__ import annotations

import argparse
from collections import Counter
from typing import Any

from pipeline_common import (
    OCR_DIR,
    REVIEW_DIR,
    annotated_image_path,
    ensure_dirs,
    normalize_text,
    page_image_path,
    page_ocr_path,
    parse_pages,
    read_json,
    write_json,
    write_jsonl,
)


def is_cjk(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff"


def ocr_paths_for_pages(pages: list[int] | None):
    return [page_ocr_path(page) for page in pages] if pages else sorted(OCR_DIR.glob("page_*.json"))


def estimate_axis_aligned_bbox(
    region_box: list[list[float]] | None,
    text_length: int,
    index: int,
) -> list[list[float]] | None:
    if not region_box or len(region_box) < 4 or text_length <= 0:
        return None
    xs = [point[0] for point in region_box]
    ys = [point[1] for point in region_box]
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    width = right - left
    char_left = left + width * (index / text_length)
    char_right = left + width * ((index + 1) / text_length)
    return [
        [char_left, top],
        [char_right, top],
        [char_right, bottom],
        [char_left, bottom],
    ]


def context(text: str, index: int, radius: int) -> str:
    start = max(0, index - radius)
    end = min(len(text), index + radius + 1)
    return text[start:end]


def build_occurrences(pages: list[int] | None) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    for path in ocr_paths_for_pages(pages):
        if not path.exists():
            raise FileNotFoundError(f"Missing OCR JSON: {path}")
        payload = read_json(path)
        page = int(payload["page"])
        annotated = payload.get("annotated_image") or str(annotated_image_path(page))
        for item in payload.get("items", []):
            region_id = item.get("token_id")
            region_text = normalize_text(item.get("text", ""))
            if not region_text:
                continue
            box = item.get("box")
            for index, char in enumerate(region_text):
                if not is_cjk(char):
                    continue
                occurrence_id = f"P{page:03d}_{region_id}_C{index:04d}"
                occurrences.append(
                    {
                        "id": occurrence_id,
                        "page": page,
                        "region_id": region_id,
                        "char": char,
                        "char_index_in_region": index,
                        "region_text": region_text,
                        "context_window_4": context(region_text, index, 4),
                        "context_window_8": context(region_text, index, 8),
                        "context_window_16": context(region_text, index, 16),
                        "ocr_confidence": item.get("confidence"),
                        "region_bbox": box,
                        "estimated_char_bbox": estimate_axis_aligned_bbox(box, len(region_text), index),
                        "crop_path": None,
                        "page_image_path": str(page_image_path(page)),
                        "annotated_page_path": annotated,
                    }
                )
    return occurrences


def write_summary(occurrences: list[dict[str, Any]]) -> None:
    by_page = Counter(item["page"] for item in occurrences)
    by_char = Counter(item["char"] for item in occurrences)
    lines = [
        "# 全字 occurrence 索引摘要",
        "",
        f"- 中文字 occurrence 數：{len(occurrences)}",
        f"- 不重複中文字：{len(by_char)}",
        f"- 頁面數：{len(by_page)}",
        "",
        "## 每頁中文字數",
        "",
    ]
    for page, count in sorted(by_page.items()):
        lines.append(f"- {page}: {count}")
    lines.extend(["", "## Top 100 字頻", ""])
    for char, count in by_char.most_common(100):
        lines.append(f"- {char}: {count}")
    (REVIEW_DIR / "char_occurrences_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build full per-character occurrence JSONL from OCR output.")
    parser.add_argument("--pages", default=None, help="Comma/range page list. Defaults to all OCR JSON files.")
    args = parser.parse_args()

    ensure_dirs()
    pages = parse_pages(args.pages) if args.pages else None
    occurrences = build_occurrences(pages)
    write_jsonl(REVIEW_DIR / "char_occurrences.jsonl", occurrences)
    write_json(
        REVIEW_DIR / "char_occurrences_meta.json",
        {
            "total_occurrences": len(occurrences),
            "pages": sorted({item["page"] for item in occurrences}),
            "unique_chars": len({item["char"] for item in occurrences}),
        },
    )
    write_summary(occurrences)
    print(f"wrote char occurrences: {len(occurrences)}")
    print(f"wrote unique chars: {len({item['char'] for item in occurrences})}")


if __name__ == "__main__":
    main()
