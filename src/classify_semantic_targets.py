from __future__ import annotations

import argparse
from collections import Counter
from typing import Any

from pipeline_common import (
    REVIEW_DIR,
    SEMANTIC_CLASSIFIER_RULES_PATH,
    ensure_dirs,
    read_json,
    read_jsonl,
    write_json,
    write_jsonl,
)


RISK_ORDER = {"high": 0, "medium": 1, "low": 2, "unresolved": 3}


DEFAULT_CLASSIFIERS: dict[str, dict[str, str]] = {
    "了": {
        "expected_bopomofo": "ㄌㄜ˙",
        "risk_level": "medium",
        "confidence": "medium",
        "reason": "未命中特定詞規則；此處「了」多半作語氣/完成助詞，先按輕聲 ㄌㄜ˙ 標記。",
    },
    "著": {
        "expected_bopomofo": "ㄓㄜ˙",
        "risk_level": "medium",
        "confidence": "medium",
        "reason": "未命中特定詞規則；此處「著」多半作動態助詞，先按輕聲 ㄓㄜ˙ 標記。",
    },
    "得": {
        "expected_bopomofo": "ㄉㄜ˙",
        "risk_level": "medium",
        "confidence": "medium",
        "reason": "未命中特定詞規則；此處「得」多半作補語/語氣連接，先按輕聲 ㄉㄜ˙ 標記。",
    },
}


def priority_rank(value: str | None) -> int:
    return RISK_ORDER.get(value or "", 9)


def rule_matches(item: dict[str, Any], rule: dict[str, Any]) -> bool:
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


def classify_target(item: dict[str, Any], rules: list[dict[str, Any]]) -> dict[str, Any]:
    candidate = dict(item)
    matched_rules = item.get("matched_rules") or []
    if item.get("expected_bopomofo"):
        candidate.update(
            {
                "classifier_status": "rule_carried",
                "classifier_source": "semantic_targets",
                "classifier_confidence": "high" if item.get("risk_level") == "high" else "medium",
                "matched_pattern": item.get("matched_phrase"),
                "priority": item.get("risk_level", "medium"),
                "status": "rule_matched",
            }
        )
        return candidate

    extra_rules = [rule for rule in rules if rule_matches(item, rule)]
    extra_rules.sort(key=lambda rule: priority_rank(rule.get("risk_level")))
    if extra_rules:
        rule = extra_rules[0]
        matched_rules = [*matched_rules, *extra_rules]
        candidate.update(
            {
                "expected_bopomofo": rule.get("expected_bopomofo"),
                "matched_phrase": rule.get("pattern"),
                "matched_pattern": rule.get("pattern"),
                "risk_level": rule.get("risk_level", "medium"),
                "priority": rule.get("risk_level", "medium"),
                "reason": rule.get("reason"),
                "classifier_status": "semantic_rule_matched",
                "classifier_source": "semantic_classifier_rules",
                "classifier_confidence": rule.get("confidence", "medium"),
                "needs_semantic_classification": False,
                "status": "semantic_classified",
                "matched_rules": matched_rules,
            }
        )
        return candidate

    default = DEFAULT_CLASSIFIERS.get(item.get("char"))
    if default:
        candidate.update(
            {
                "expected_bopomofo": default["expected_bopomofo"],
                "matched_phrase": None,
                "matched_pattern": None,
                "risk_level": default["risk_level"],
                "priority": default["risk_level"],
                "reason": default["reason"],
                "classifier_status": "default_by_char_context",
                "classifier_source": "semantic_default",
                "classifier_confidence": default["confidence"],
                "needs_semantic_classification": False,
                "status": "semantic_classified",
                "matched_rules": matched_rules,
            }
        )
        return candidate

    candidate.update(
        {
            "matched_pattern": item.get("matched_phrase"),
            "priority": "unresolved",
            "risk_level": "unresolved",
            "classifier_status": "semantic_unresolved",
            "classifier_source": None,
            "classifier_confidence": "none",
            "status": "semantic_unresolved",
            "needs_semantic_classification": True,
            "reason": "仍無足夠規則判讀理論讀音，保留給人工或後續 LLM 判斷。",
            "matched_rules": matched_rules,
        }
    )
    return candidate


def enrich_with_phrase_crops(candidates: list[dict[str, Any]]) -> None:
    phrase_path = REVIEW_DIR / "phrase_occurrences.json"
    if not phrase_path.exists():
        return
    phrase_items = read_json(phrase_path)
    phrase_by_id = {
        f"P{int(item['page']):03d}_{item['token_id']}_C{int(item['char_index']):04d}": item
        for item in phrase_items
    }
    for candidate in candidates:
        phrase = phrase_by_id.get(candidate.get("char_occurrence_id"))
        if not phrase:
            continue
        candidate["phrase_crop_image"] = phrase.get("phrase_crop_image")
        candidate["candidate_phrase"] = phrase.get("candidate_phrase")
        candidate["phrase_options"] = phrase.get("phrase_options")
        candidate["annotated_image"] = phrase.get("annotated_image")
        candidate["token_id"] = phrase.get("token_id")
        candidate["char_index"] = phrase.get("char_index")


def write_summary(candidates: list[dict[str, Any]]) -> None:
    by_status = Counter(item.get("classifier_status") for item in candidates)
    by_char = Counter(item.get("char") for item in candidates)
    by_priority = Counter(item.get("priority") for item in candidates)
    lines = [
        "# Semantic classifier 摘要",
        "",
        f"- review candidates：{len(candidates)}",
        f"- 已有讀音：{sum(1 for item in candidates if item.get('expected_bopomofo'))}",
        f"- 仍未解析：{sum(1 for item in candidates if not item.get('expected_bopomofo'))}",
        "",
        "## Classifier Status",
        "",
    ]
    for status, count in by_status.most_common():
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Priority", ""])
    for priority, count in by_priority.most_common():
        lines.append(f"- {priority}: {count}")
    lines.extend(["", "## 字分布", ""])
    for char, count in by_char.most_common():
        lines.append(f"- {char}: {count}")
    (REVIEW_DIR / "semantic_classifier_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify semantic targets by context rules.")
    parser.parse_args()

    ensure_dirs()
    targets = read_jsonl(REVIEW_DIR / "semantic_targets.jsonl")
    if not targets:
        raise FileNotFoundError("Missing outputs/review/semantic_targets.jsonl. Run build_semantic_targets.py first.")
    rules = read_json(SEMANTIC_CLASSIFIER_RULES_PATH)
    candidates = [classify_target(item, rules) for item in targets]
    enrich_with_phrase_crops(candidates)
    candidates.sort(
        key=lambda item: (
            priority_rank(item.get("priority")),
            int(item.get("page", 0)),
            str(item.get("region_id", "")),
            int(item.get("char_index_in_region", 0)),
        )
    )
    write_jsonl(REVIEW_DIR / "semantic_review_candidates.jsonl", candidates)
    write_json(REVIEW_DIR / "semantic_review_candidates.json", candidates)
    write_json(
        REVIEW_DIR / "semantic_review_candidates_meta.json",
        {
            "total": len(candidates),
            "classified": sum(1 for item in candidates if item.get("expected_bopomofo")),
            "unresolved": sum(1 for item in candidates if not item.get("expected_bopomofo")),
        },
    )
    write_summary(candidates)
    print(f"wrote semantic review candidates: {len(candidates)}")
    print(f"classified: {sum(1 for item in candidates if item.get('expected_bopomofo'))}")
    print(f"unresolved: {sum(1 for item in candidates if not item.get('expected_bopomofo'))}")


if __name__ == "__main__":
    main()
