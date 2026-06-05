from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_PDF = PROJECT_ROOT / "data" / "raw" / "sample.pdf"
RISK_TERMS_PATH = PROJECT_ROOT / "data" / "risk_terms.json"
POLYPHONIC_CHARS_PATH = PROJECT_ROOT / "data" / "polyphonic_chars.json"
READING_RULES_PATH = PROJECT_ROOT / "data" / "reading_rules.json"
SEMANTIC_CLASSIFIER_RULES_PATH = PROJECT_ROOT / "data" / "semantic_classifier_rules.json"
PAGES_DIR = PROJECT_ROOT / "outputs" / "pages"
OCR_DIR = PROJECT_ROOT / "outputs" / "ocr"
REVIEW_DIR = PROJECT_ROOT / "outputs" / "review"
CROPS_DIR = REVIEW_DIR / "crops"

DEFAULT_PAGES = [
    1,
    4,
    5,
    13,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    26,
    27,
    30,
    31,
    32,
    33,
    34,
    35,
    36,
    37,
    38,
    39,
    40,
    41,
    42,
]


def ensure_dirs() -> None:
    for path in (PAGES_DIR, OCR_DIR, REVIEW_DIR, CROPS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def page_image_path(page: int) -> Path:
    return PAGES_DIR / f"page_{page:03d}.png"


def annotated_image_path(page: int) -> Path:
    return PAGES_DIR / f"page_{page:03d}_annotated.png"


def page_ocr_path(page: int) -> Path:
    return OCR_DIR / f"page_{page:03d}.json"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, ensure_ascii=False) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def parse_pages(value: str | None) -> list[int]:
    if not value:
        return DEFAULT_PAGES
    pages: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = [int(x.strip()) for x in part.split("-", 1)]
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))
    return sorted(dict.fromkeys(pages))


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def find_matches(text: str, risk_terms: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = normalize_text(text)
    matches: list[dict[str, Any]] = []
    for term in risk_terms:
        matched_word = term["matched_word"]
        if matched_word in normalized:
            matches.append(term)
    return matches
