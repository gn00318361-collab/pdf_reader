from __future__ import annotations

import argparse
from collections import defaultdict
from typing import Any

from PIL import Image, ImageDraw

from pipeline_common import PAGES_DIR, REVIEW_DIR, ensure_dirs, read_json, write_json


PHRASE_CROPS_DIR = REVIEW_DIR / "phrase_crops"


def is_cjk(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff"


def cjk_run_bounds(text: str, index: int) -> tuple[int, int]:
    start = index
    while start > 0 and is_cjk(text[start - 1]):
        start -= 1
    end = index + 1
    while end < len(text) and is_cjk(text[end]):
        end += 1
    return start, end


def phrase_bounds(text: str, index: int, left: int, right: int) -> tuple[int, int]:
    run_start, run_end = cjk_run_bounds(text, index)
    start = max(run_start, index - left)
    end = min(run_end, index + right + 1)
    return start, end


def phrase_options(text: str, index: int) -> dict[str, str]:
    run_start, run_end = cjk_run_bounds(text, index)
    options: dict[str, str] = {}
    if index - 1 >= run_start:
        options["left_bigram"] = text[index - 1 : index + 1]
    if index + 2 <= run_end:
        options["right_bigram"] = text[index : index + 2]
    if index - 1 >= run_start and index + 2 <= run_end:
        options["trigram"] = text[index - 1 : index + 2]
    start, end = phrase_bounds(text, index, 2, 2)
    options["window"] = text[start:end]
    return options


def estimate_axis_aligned_bbox(region_box: list[list[float]], text_length: int, start: int, end: int) -> list[list[float]]:
    xs = [point[0] for point in region_box]
    ys = [point[1] for point in region_box]
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    if text_length <= 0:
        return [[left, top], [right, top], [right, bottom], [left, bottom]]

    width = right - left
    phrase_left = left + width * (start / text_length)
    phrase_right = left + width * (end / text_length)
    return [
        [phrase_left, top],
        [phrase_right, top],
        [phrase_right, bottom],
        [phrase_left, bottom],
    ]


def expand_bbox(box: list[list[float]], image_size: tuple[int, int], pad_x: int = 72, pad_y: int = 44) -> tuple[int, int, int, int]:
    width, height = image_size
    xs = [point[0] for point in box]
    ys = [point[1] for point in box]
    return (
        max(0, int(min(xs) - pad_x)),
        max(0, int(min(ys) - pad_y)),
        min(width, int(max(xs) + pad_x)),
        min(height, int(max(ys) + pad_y)),
    )


def draw_highlight(crop: Image.Image, box: list[list[float]], origin: tuple[int, int]) -> Image.Image:
    image = crop.convert("RGBA")
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    ox, oy = origin
    polygon = [(point[0] - ox, point[1] - oy) for point in box]
    draw.polygon(polygon, fill=(255, 106, 0, 70), outline=(230, 76, 0, 240))
    return Image.alpha_composite(image, overlay).convert("RGB")


def crop_name(item: dict[str, Any]) -> str:
    return (
        f"page_{int(item['page']):03d}_"
        f"{item['token_id']}_"
        f"{item['char']}_{item['char_index']}.webp"
    )


def generate_phrase_crop(item: dict[str, Any], image_cache: dict[int, Image.Image]) -> None:
    page = int(item["page"])
    image = image_cache.get(page)
    if image is None:
        image_path = PAGES_DIR / f"page_{page:03d}.png"
        if not image_path.exists():
            return
        image = Image.open(image_path).convert("RGB")
        image_cache[page] = image

    box = item.get("estimated_phrase_box") or []
    if len(box) < 4:
        return
    left, top, right, bottom = expand_bbox(box, image.size)
    if right <= left or bottom <= top:
        return
    crop = image.crop((left, top, right, bottom))
    crop = draw_highlight(crop, box, (left, top))
    PHRASE_CROPS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PHRASE_CROPS_DIR / crop_name(item)
    crop.save(out_path, "WEBP", quality=82, method=6)
    item["phrase_crop_image"] = str(out_path)


def build_phrase_occurrences(char_index: dict[str, Any], left: int, right: int) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    image_cache: dict[int, Image.Image] = {}

    for char, items in char_index.get("by_char", {}).items():
        for item in items:
            text = item["region_text"]
            index = int(item["char_index"])
            if index >= len(text) or text[index] != char:
                continue
            start, end = phrase_bounds(text, index, left, right)
            phrase = text[start:end]
            estimated_box = estimate_axis_aligned_bbox(item.get("box") or [], len(text), start, end)
            occurrence = {
                "page": item["page"],
                "token_id": item["token_id"],
                "char": char,
                "char_index": index,
                "candidate_phrase": phrase,
                "phrase_start": start,
                "phrase_end": end,
                "phrase_options": phrase_options(text, index),
                "before": item.get("before"),
                "after": item.get("after"),
                "context": item.get("context"),
                "region_text": text,
                "readings": item.get("readings", []),
                "note": item.get("note", ""),
                "region_box": item.get("box"),
                "estimated_phrase_box": estimated_box,
                "annotated_image": item.get("annotated_image"),
            }
            generate_phrase_crop(occurrence, image_cache)
            occurrences.append(occurrence)
    return occurrences


def build_phrase_terms(occurrences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in occurrences:
        grouped[(item["char"], item["candidate_phrase"])].append(item)

    terms: list[dict[str, Any]] = []
    for (char, phrase), items in grouped.items():
        pages = sorted({int(item["page"]) for item in items})
        terms.append(
            {
                "char": char,
                "candidate_phrase": phrase,
                "count": len(items),
                "pages": pages,
                "readings": items[0].get("readings", []),
                "sample_occurrences": [
                    {
                        "page": item["page"],
                        "token_id": item["token_id"],
                        "region_text": item["region_text"],
                        "phrase_options": item["phrase_options"],
                    }
                    for item in items[:5]
                ],
            }
        )
    return sorted(terms, key=lambda item: (-item["count"], item["char"], item["candidate_phrase"]))


def write_summary(occurrences: list[dict[str, Any]], terms: list[dict[str, Any]]) -> None:
    lines = [
        "# 詞級多音字候選摘要",
        "",
        f"- 詞級 occurrence 數：{len(occurrences)}",
        f"- 不重複候選短語數：{len(terms)}",
        "",
        "## Top 候選短語",
        "",
        "| 字 | 候選短語 | 次數 | 頁碼 | 讀音 |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for item in terms[:120]:
        pages = ", ".join(str(page) for page in item["pages"][:12])
        if len(item["pages"]) > 12:
            pages += ", ..."
        readings = " / ".join(item.get("readings", []))
        lines.append(f"| {item['char']} | {item['candidate_phrase']} | {item['count']} | {pages} | {readings} |")
    (REVIEW_DIR / "phrase_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build phrase-level candidates from the finite polyphonic char index.")
    parser.add_argument("--left", type=int, default=2, help="Estimated phrase chars before the target char.")
    parser.add_argument("--right", type=int, default=2, help="Estimated phrase chars after the target char.")
    args = parser.parse_args()

    ensure_dirs()
    char_index_path = REVIEW_DIR / "char_index.json"
    if not char_index_path.exists():
        raise FileNotFoundError("Missing outputs/review/char_index.json. Run build_corpus_index.py first.")
    char_index = read_json(char_index_path)
    occurrences = build_phrase_occurrences(char_index, args.left, args.right)
    terms = build_phrase_terms(occurrences)

    write_json(REVIEW_DIR / "phrase_occurrences.json", occurrences)
    write_json(REVIEW_DIR / "phrase_terms.json", terms)
    write_summary(occurrences, terms)
    print(f"wrote phrase occurrences: {len(occurrences)}")
    print(f"wrote phrase terms: {len(terms)}")


if __name__ == "__main__":
    main()

