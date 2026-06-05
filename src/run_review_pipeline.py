from __future__ import annotations

import argparse

from build_char_occurrences import build_occurrences, write_summary as write_char_summary
from build_corpus_index import build_char_index, build_context_candidates, build_corpus, load_polyphonic_chars
from build_phrase_index import build_phrase_occurrences, build_phrase_terms, write_summary as write_phrase_summary
from build_review_dashboard import build_review_dashboard
from build_semantic_targets import load_phrase_rules, load_polyphonic_meta, target_from_occurrence, write_summary as write_targets_summary
from classify_semantic_targets import classify_target, enrich_with_phrase_crops, write_summary as write_classifier_summary
from ocr_pages import ocr_pages
from pipeline_common import REVIEW_DIR, ensure_dirs, parse_pages, write_json, write_jsonl
from render_pages import render_pages


DEFAULT_REVIEW_PAGES = "1,4,5,13,15,16-27,30-42"


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild OCR outputs, semantic review candidates, and dashboard.")
    parser.add_argument("--pages", default=DEFAULT_REVIEW_PAGES, help="Comma/range page list for review.")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--engine", choices=["auto", "paddle", "rapidocr"], default="rapidocr")
    parser.add_argument("--gpu", action="store_true", help="Use GPU OCR runtime when available.")
    parser.add_argument("--context-radius", type=int, default=4)
    parser.add_argument("--phrase-left", type=int, default=2)
    parser.add_argument("--phrase-right", type=int, default=2)
    parser.add_argument("--low-confidence", type=float, default=0.85)
    parser.add_argument("--skip-ocr", action="store_true", help="Reuse existing outputs/ocr JSON files.")
    args = parser.parse_args()

    ensure_dirs()
    pages = parse_pages(args.pages)
    if not args.skip_ocr:
        render_pages(pages, args.dpi)
        ocr_pages(pages, use_gpu=args.gpu, engine=args.engine)

    polyphonic_chars = load_polyphonic_chars()
    corpus = build_corpus(pages)
    char_index = build_char_index(corpus, polyphonic_chars, args.context_radius)
    context_candidates = build_context_candidates(char_index)
    write_json(REVIEW_DIR / "corpus.json", corpus)
    write_json(REVIEW_DIR / "char_index.json", char_index)
    write_json(REVIEW_DIR / "context_candidates.json", context_candidates)

    phrase_occurrences = build_phrase_occurrences(char_index, args.phrase_left, args.phrase_right)
    phrase_terms = build_phrase_terms(phrase_occurrences)
    write_json(REVIEW_DIR / "phrase_occurrences.json", phrase_occurrences)
    write_json(REVIEW_DIR / "phrase_terms.json", phrase_terms)
    write_phrase_summary(phrase_occurrences, phrase_terms)

    char_occurrences = build_occurrences(pages)
    write_jsonl(REVIEW_DIR / "char_occurrences.jsonl", char_occurrences)
    write_json(
        REVIEW_DIR / "char_occurrences_meta.json",
        {
            "total_occurrences": len(char_occurrences),
            "pages": sorted({item["page"] for item in char_occurrences}),
            "unique_chars": len({item["char"] for item in char_occurrences}),
        },
    )
    write_char_summary(char_occurrences)

    polyphonic_meta = load_polyphonic_meta()
    phrase_rules = load_phrase_rules()
    semantic_targets = [
        target
        for item in char_occurrences
        if (target := target_from_occurrence(item, polyphonic_meta, phrase_rules, args.low_confidence)) is not None
    ]
    semantic_targets.sort(key=lambda item: (int(item["page"]), str(item["region_id"]), int(item["char_index_in_region"])))
    write_jsonl(REVIEW_DIR / "semantic_targets.jsonl", semantic_targets)
    write_json(
        REVIEW_DIR / "semantic_targets_meta.json",
        {
            "total_char_occurrences": len(char_occurrences),
            "semantic_targets": len(semantic_targets),
            "needs_semantic_classification": sum(
                1 for item in semantic_targets if item.get("needs_semantic_classification")
            ),
            "low_confidence_threshold": args.low_confidence,
        },
    )
    write_targets_summary(semantic_targets, len(char_occurrences))

    from pipeline_common import SEMANTIC_CLASSIFIER_RULES_PATH, read_json

    classifier_rules = read_json(SEMANTIC_CLASSIFIER_RULES_PATH)
    review_candidates = [classify_target(item, classifier_rules) for item in semantic_targets]
    enrich_with_phrase_crops(review_candidates)
    review_candidates.sort(
        key=lambda item: (
            {"high": 0, "medium": 1, "low": 2, "unresolved": 3}.get(item.get("priority", ""), 9),
            int(item.get("page", 0)),
            str(item.get("region_id", "")),
            int(item.get("char_index_in_region", 0)),
        )
    )
    write_jsonl(REVIEW_DIR / "semantic_review_candidates.jsonl", review_candidates)
    write_json(REVIEW_DIR / "semantic_review_candidates.json", review_candidates)
    write_json(
        REVIEW_DIR / "semantic_review_candidates_meta.json",
        {
            "total": len(review_candidates),
            "classified": sum(1 for item in review_candidates if item.get("expected_bopomofo")),
            "unresolved": sum(1 for item in review_candidates if not item.get("expected_bopomofo")),
        },
    )
    write_classifier_summary(review_candidates)
    dashboard_path = build_review_dashboard()

    print(f"review candidates: {len(review_candidates)}")
    print(f"classified: {sum(1 for item in review_candidates if item.get('expected_bopomofo'))}")
    print(f"unresolved: {sum(1 for item in review_candidates if not item.get('expected_bopomofo'))}")
    print(f"dashboard: {dashboard_path}")


if __name__ == "__main__":
    main()
