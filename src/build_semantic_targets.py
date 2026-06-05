from __future__ import annotations

import argparse
from collections import Counter
from typing import Any

from pipeline_common import (
    POLYPHONIC_CHARS_PATH,
    READING_RULES_PATH,
    REVIEW_DIR,
    RISK_TERMS_PATH,
    ensure_dirs,
    read_json,
    read_jsonl,
    write_json,
    write_jsonl,
)


def load_polyphonic_meta() -> dict[str, dict[str, Any]]:
    return {item["char"]: item for item in read_json(POLYPHONIC_CHARS_PATH)}


def load_phrase_rules() -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for term in read_json(RISK_TERMS_PATH):
        rules.append(
            {
                "source": "risk_terms",
                "char": term.get("target_char"),
                "pattern": term.get("matched_word"),
                "expected_bopomofo": term.get("expected_bopomofo"),
                "priority": term.get("confidence", "medium"),
                "reason": term.get("reason"),
            }
        )
    for rule in read_json(READING_RULES_PATH):
        rules.append(
            {
                "source": "reading_rules",
                "char": rule.get("char"),
                "pattern": rule.get("pattern"),
                "expected_bopomofo": rule.get("expected_bopomofo"),
                "priority": rule.get("priority", "medium"),
                "reason": rule.get("reason"),
            }
        )
    return rules


def phrase_rule_matches(item: dict[str, Any], rule: dict[str, Any]) -> bool:
    char = rule.get("char")
    pattern = rule.get("pattern")
    if not char or not pattern or item.get("char") != char:
        return False
    text = item.get("region_text", "")
    target_index = int(item.get("char_index_in_region", -1))
    start = 0
    while True:
        found = text.find(pattern, start)
        if found < 0:
            return False
        offset = target_index - found
        if 0 <= offset < len(pattern) and pattern[offset] == char:
            return True
        start = found + 1


def priority_rank(priority: str | None) -> int:
    order = {"high": 0, "medium": 1, "low": 2}
    return order.get(priority or "", 9)


def target_from_occurrence(
    item: dict[str, Any],
    polyphonic_meta: dict[str, dict[str, Any]],
    phrase_rules: list[dict[str, Any]],
    low_confidence: float,
) -> dict[str, Any] | None:
    char = item.get("char")
    triggers: list[str] = []
    matched_rules = [rule for rule in phrase_rules if phrase_rule_matches(item, rule)]
    matched_rules.sort(key=lambda rule: priority_rank(rule.get("priority")))
    is_polyphonic = char in polyphonic_meta

    if is_polyphonic:
        triggers.append("polyphonic_char")
    if matched_rules:
        triggers.append("phrase_rule_match")

    confidence = item.get("ocr_confidence")
    if is_polyphonic and isinstance(confidence, (int, float)) and confidence < low_confidence:
        triggers.append("low_confidence_polyphonic")

    if not triggers:
        return None

    best_rule = matched_rules[0] if matched_rules else {}
    meta = polyphonic_meta.get(char, {})
    return {
        "id": item["id"],
        "char_occurrence_id": item["id"],
        "page": item["page"],
        "region_id": item["region_id"],
        "char": char,
        "char_index_in_region": item["char_index_in_region"],
        "region_text": item["region_text"],
        "context_window_4": item["context_window_4"],
        "context_window_8": item["context_window_8"],
        "context_window_16": item["context_window_16"],
        "triggers": sorted(set(triggers)),
        "readings": meta.get("readings", []),
        "note": meta.get("note", ""),
        "matched_phrase": best_rule.get("pattern"),
        "expected_bopomofo": best_rule.get("expected_bopomofo"),
        "risk_level": best_rule.get("priority") or ("medium" if is_polyphonic else "low"),
        "reason": best_rule.get("reason") or "此字在多音字表中，需依語境判斷理論讀音。",
        "needs_semantic_classification": not bool(best_rule.get("expected_bopomofo")),
        "needs_review": True,
        "matched_rules": matched_rules,
        "ocr_confidence": item.get("ocr_confidence"),
        "estimated_char_bbox": item.get("estimated_char_bbox"),
        "crop_path": item.get("crop_path"),
        "page_image_path": item.get("page_image_path"),
        "annotated_page_path": item.get("annotated_page_path"),
    }


def write_summary(targets: list[dict[str, Any]], total_char_occurrences: int) -> None:
    by_char = Counter(item["char"] for item in targets)
    by_trigger = Counter(trigger for item in targets for trigger in item.get("triggers", []))
    by_risk = Counter(item.get("risk_level") for item in targets)
    lines = [
        "# Semantic targets 摘要",
        "",
        f"- 全字 occurrence 數：{total_char_occurrences}",
        f"- semantic target 數：{len(targets)}",
        f"- 需要語意 classifier 補判：{sum(1 for item in targets if item.get('needs_semantic_classification'))}",
        "",
        "## Risk Level",
        "",
    ]
    for risk, count in by_risk.most_common():
        lines.append(f"- {risk}: {count}")
    lines.extend(["", "## Triggers", ""])
    for trigger, count in by_trigger.most_common():
        lines.append(f"- {trigger}: {count}")
    lines.extend(["", "## 字分布", ""])
    for char, count in by_char.most_common():
        lines.append(f"- {char}: {count}")
    (REVIEW_DIR / "semantic_targets_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build semantic review targets from full char occurrences.")
    parser.add_argument("--low-confidence", type=float, default=0.85, help="OCR confidence threshold for extra flags.")
    args = parser.parse_args()

    ensure_dirs()
    occurrences_path = REVIEW_DIR / "char_occurrences.jsonl"
    occurrences = read_jsonl(occurrences_path)
    if not occurrences:
        raise FileNotFoundError("Missing outputs/review/char_occurrences.jsonl. Run build_char_occurrences.py first.")

    polyphonic_meta = load_polyphonic_meta()
    phrase_rules = load_phrase_rules()
    targets = [
        target
        for item in occurrences
        if (target := target_from_occurrence(item, polyphonic_meta, phrase_rules, args.low_confidence)) is not None
    ]
    targets.sort(key=lambda item: (int(item["page"]), str(item["region_id"]), int(item["char_index_in_region"])))

    write_jsonl(REVIEW_DIR / "semantic_targets.jsonl", targets)
    write_json(
        REVIEW_DIR / "semantic_targets_meta.json",
        {
            "total_char_occurrences": len(occurrences),
            "semantic_targets": len(targets),
            "needs_semantic_classification": sum(1 for item in targets if item.get("needs_semantic_classification")),
            "low_confidence_threshold": args.low_confidence,
        },
    )
    write_summary(targets, len(occurrences))
    print(f"wrote semantic targets: {len(targets)}")
    print(f"needs semantic classification: {sum(1 for item in targets if item.get('needs_semantic_classification'))}")


if __name__ == "__main__":
    main()
