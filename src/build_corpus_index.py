from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from typing import Any

from pipeline_common import (
    OCR_DIR,
    POLYPHONIC_CHARS_PATH,
    REVIEW_DIR,
    ensure_dirs,
    normalize_text,
    page_ocr_path,
    parse_pages,
    read_json,
    write_json,
)


def load_polyphonic_chars() -> list[dict[str, Any]]:
    return read_json(POLYPHONIC_CHARS_PATH)


def ocr_paths_for_pages(pages: list[int] | None):
    return [page_ocr_path(page) for page in pages] if pages else sorted(OCR_DIR.glob("page_*.json"))


def build_corpus(pages: list[int] | None) -> dict[str, Any]:
    regions: list[dict[str, Any]] = []
    page_texts: dict[str, str] = {}

    for path in ocr_paths_for_pages(pages):
        if not path.exists():
            raise FileNotFoundError(f"Missing OCR JSON: {path}")
        payload = read_json(path)
        page = int(payload["page"])
        region_texts: list[str] = []
        for item in payload.get("items", []):
            text = normalize_text(item.get("text", ""))
            if not text:
                continue
            region = {
                "page": page,
                "token_id": item.get("token_id"),
                "text": text,
                "confidence": item.get("confidence"),
                "box": item.get("box"),
                "annotated_image": payload.get("annotated_image"),
            }
            regions.append(region)
            region_texts.append(text)
        page_texts[str(page)] = "\n".join(region_texts)

    full_text = "\n".join(page_texts[str(page)] for page in sorted(int(p) for p in page_texts))
    return {
        "region_count": len(regions),
        "pages": sorted(int(page) for page in page_texts),
        "full_text": full_text,
        "regions": regions,
    }


def context_window(text: str, index: int, radius: int) -> dict[str, str]:
    before = text[max(0, index - radius) : index]
    char = text[index]
    after = text[index + 1 : index + 1 + radius]
    return {
        "before": before,
        "char": char,
        "after": after,
        "context": f"{before}{char}{after}",
    }


def build_char_index(corpus: dict[str, Any], polyphonic_chars: list[dict[str, Any]], radius: int) -> dict[str, Any]:
    char_meta = {item["char"]: item for item in polyphonic_chars}
    target_chars = set(char_meta)
    by_char: dict[str, list[dict[str, Any]]] = defaultdict(list)
    phrase_counts: Counter[str] = Counter()

    for region in corpus["regions"]:
        text = region["text"]
        for index, char in enumerate(text):
            if char not in target_chars:
                continue
            window = context_window(text, index, radius)
            phrase_counts[window["context"]] += 1
            by_char[char].append(
                {
                    "page": region["page"],
                    "token_id": region["token_id"],
                    "char": char,
                    "char_index": index,
                    "before": window["before"],
                    "after": window["after"],
                    "context": window["context"],
                    "region_text": text,
                    "confidence": region.get("confidence"),
                    "box": region.get("box"),
                    "annotated_image": region.get("annotated_image"),
                    "readings": char_meta[char].get("readings", []),
                    "note": char_meta[char].get("note", ""),
                }
            )

    summary = {
        char: {
            "count": len(items),
            "readings": char_meta[char].get("readings", []),
            "note": char_meta[char].get("note", ""),
            "sample_contexts": [context for context, _ in Counter(item["context"] for item in items).most_common(10)],
        }
        for char, items in sorted(by_char.items(), key=lambda pair: (-len(pair[1]), pair[0]))
    }

    return {
        "radius": radius,
        "total_occurrences": sum(len(items) for items in by_char.values()),
        "summary": summary,
        "by_char": dict(by_char),
        "top_contexts": [{"context": context, "count": count} for context, count in phrase_counts.most_common(100)],
    }


def build_context_candidates(char_index: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for char, items in char_index["by_char"].items():
        for item in items:
            key = (char, item["context"], item["region_text"])
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "char": char,
                    "context": item["context"],
                    "before": item["before"],
                    "after": item["after"],
                    "readings": item["readings"],
                    "note": item["note"],
                    "example_page": item["page"],
                    "example_token_id": item["token_id"],
                    "example_region_text": item["region_text"],
                }
            )
    return sorted(candidates, key=lambda item: (item["char"], item["context"]))


def write_summary(corpus: dict[str, Any], char_index: dict[str, Any], context_candidates: list[dict[str, Any]]) -> None:
    lines = [
        "# Corpus 多音字上下文索引摘要",
        "",
        f"- 頁面：{', '.join(str(page) for page in corpus['pages'])}",
        f"- OCR region 數：{corpus['region_count']}",
        f"- 多音字出現次數：{char_index['total_occurrences']}",
        f"- 不重複上下文候選：{len(context_candidates)}",
        "",
        "## 多音字分布",
        "",
        "| 字 | 次數 | 讀音 | 樣本上下文 |",
        "| --- | ---: | --- | --- |",
    ]
    for char, meta in char_index["summary"].items():
        readings = " / ".join(meta.get("readings", []))
        samples = "；".join(meta.get("sample_contexts", [])[:5])
        lines.append(f"| {char} | {meta['count']} | {readings} | {samples} |")

    lines.extend(
        [
            "",
            "## Top Contexts",
            "",
        ]
    )
    for item in char_index["top_contexts"][:50]:
        lines.append(f"- {item['count']} × `{item['context']}`")

    (REVIEW_DIR / "corpus_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build finite corpus and polyphonic character context index from OCR JSON.")
    parser.add_argument("--pages", default=None, help="Comma/range page list. Defaults to all OCR JSON files.")
    parser.add_argument("--radius", type=int, default=4, help="Characters before/after each polyphonic char.")
    args = parser.parse_args()

    ensure_dirs()
    pages = parse_pages(args.pages) if args.pages else None
    polyphonic_chars = load_polyphonic_chars()
    corpus = build_corpus(pages)
    char_index = build_char_index(corpus, polyphonic_chars, args.radius)
    context_candidates = build_context_candidates(char_index)

    write_json(REVIEW_DIR / "corpus.json", corpus)
    write_json(REVIEW_DIR / "char_index.json", char_index)
    write_json(REVIEW_DIR / "context_candidates.json", context_candidates)
    write_summary(corpus, char_index, context_candidates)
    print(f"wrote corpus regions: {corpus['region_count']}")
    print(f"wrote polyphonic occurrences: {char_index['total_occurrences']}")
    print(f"wrote context candidates: {len(context_candidates)}")


if __name__ == "__main__":
    main()
