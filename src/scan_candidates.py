from __future__ import annotations

import argparse
from typing import Any

from pipeline_common import (
    OCR_DIR,
    REVIEW_DIR,
    RISK_TERMS_PATH,
    ensure_dirs,
    find_matches,
    normalize_text,
    page_ocr_path,
    parse_pages,
    read_json,
    write_json,
)


def context_for(page_text: str, matched_word: str, radius: int = 18) -> str:
    normalized = normalize_text(page_text)
    index = normalized.find(matched_word)
    if index < 0:
        return ""
    start = max(0, index - radius)
    end = min(len(normalized), index + len(matched_word) + radius)
    return normalized[start:end]


def candidate_from_item(page_payload: dict[str, Any], item: dict[str, Any], term: dict[str, Any]) -> dict[str, Any]:
    return {
        "page": page_payload["page"],
        "token_id": item.get("token_id"),
        "text": item.get("text"),
        "matched_word": term["matched_word"],
        "target_char": term["target_char"],
        "expected_bopomofo": term["expected_bopomofo"],
        "reason": term["reason"],
        "rule_confidence": term.get("confidence"),
        "ocr_confidence": item.get("confidence"),
        "box": item.get("box"),
        "annotated_image": page_payload.get("annotated_image"),
        "ocr_context": context_for(page_payload.get("text", ""), term["matched_word"]),
    }


def scan_pages(pages: list[int] | None) -> list[dict[str, Any]]:
    ensure_dirs()
    risk_terms = read_json(RISK_TERMS_PATH)
    candidates: list[dict[str, Any]] = []

    ocr_paths = [page_ocr_path(page) for page in pages] if pages else sorted(OCR_DIR.glob("page_*.json"))
    for ocr_path in ocr_paths:
        if not ocr_path.exists():
            raise FileNotFoundError(f"Missing OCR JSON: {ocr_path}")
        page_payload = read_json(ocr_path)
        for item in page_payload.get("items", []):
            matches = item.get("matched_risk_terms") or find_matches(item.get("text", ""), risk_terms)
            for term in matches:
                candidates.append(candidate_from_item(page_payload, item, term))

    out_path = REVIEW_DIR / "review_candidates.json"
    write_json(out_path, candidates)
    print(f"wrote {len(candidates)} candidates -> {out_path}")
    return candidates


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan OCR JSON for high-risk Mandarin terms.")
    parser.add_argument("--pages", default=None, help="Comma/range page list. Defaults to all OCR JSON files.")
    args = parser.parse_args()

    scan_pages(parse_pages(args.pages) if args.pages else None)


if __name__ == "__main__":
    main()

