from __future__ import annotations

import argparse
from collections import Counter
from typing import Any

from pipeline_common import READING_RULES_PATH, REVIEW_DIR, ensure_dirs, read_json, write_json


PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2, "unresolved": 3}


def rule_matches(item: dict[str, Any], rule: dict[str, Any]) -> bool:
    if item.get("char") != rule.get("char"):
        return False
    pattern = rule.get("pattern", "")
    phrase_options = item.get("phrase_options") or {}
    haystacks = [
        item.get("candidate_phrase", ""),
        item.get("context", ""),
        *(value for value in phrase_options.values() if isinstance(value, str)),
    ]
    return bool(pattern) and any(pattern in text for text in haystacks)


def score_item(item: dict[str, Any], rules: list[dict[str, Any]]) -> dict[str, Any]:
    matched_rules = [rule for rule in rules if rule_matches(item, rule)]
    scored = dict(item)
    if matched_rules:
        matched_rules.sort(key=lambda rule: PRIORITY_ORDER.get(rule.get("priority", "medium"), 9))
        rule = matched_rules[0]
        scored.update(
            {
                "status": "rule_matched",
                "priority": rule.get("priority", "medium"),
                "matched_pattern": rule.get("pattern"),
                "expected_bopomofo": rule.get("expected_bopomofo"),
                "reason": rule.get("reason"),
                "matched_rules": matched_rules,
            }
        )
    else:
        scored.update(
            {
                "status": "unresolved",
                "priority": "unresolved",
                "matched_pattern": None,
                "expected_bopomofo": None,
                "reason": "尚無規則命中；保留為有限 corpus 中的多音字上下文候選。",
                "matched_rules": [],
            }
        )
    return scored


def score_candidates() -> list[dict[str, Any]]:
    phrase_path = REVIEW_DIR / "phrase_occurrences.json"
    if not phrase_path.exists():
        raise FileNotFoundError("Missing outputs/review/phrase_occurrences.json. Run build_phrase_index.py first.")

    occurrences = read_json(phrase_path)
    rules = read_json(READING_RULES_PATH)
    scored = [score_item(item, rules) for item in occurrences]
    scored.sort(
        key=lambda item: (
            PRIORITY_ORDER.get(item.get("priority", "unresolved"), 9),
            int(item.get("page", 0)),
            str(item.get("token_id", "")),
            str(item.get("char", "")),
        )
    )
    return scored


def write_summary(scored: list[dict[str, Any]]) -> None:
    by_status = Counter(item["status"] for item in scored)
    by_priority = Counter(item["priority"] for item in scored)
    by_char = Counter(item["char"] for item in scored if item["status"] == "rule_matched")
    by_pattern = Counter(item.get("matched_pattern") for item in scored if item.get("matched_pattern"))

    lines = [
        "# 詞級候選判讀摘要",
        "",
        f"- 總 occurrence：{len(scored)}",
        f"- 規則命中：{by_status.get('rule_matched', 0)}",
        f"- 未解析：{by_status.get('unresolved', 0)}",
        "",
        "## Priority",
        "",
    ]
    for priority, count in by_priority.most_common():
        lines.append(f"- {priority}: {count}")

    lines.extend(["", "## 規則命中字分布", ""])
    for char, count in by_char.most_common():
        lines.append(f"- {char}: {count}")

    lines.extend(["", "## Top Patterns", ""])
    for pattern, count in by_pattern.most_common(50):
        lines.append(f"- {count} × `{pattern}`")

    (REVIEW_DIR / "scored_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Score finite phrase-level candidates with corpus-scoped reading rules.")
    parser.parse_args()

    ensure_dirs()
    scored = score_candidates()
    reviewable = [item for item in scored if item["status"] == "rule_matched"]
    write_json(REVIEW_DIR / "scored_phrase_candidates.json", scored)
    write_json(REVIEW_DIR / "reviewable_phrase_candidates.json", reviewable)
    write_summary(scored)
    print(f"wrote scored phrase candidates: {len(scored)}")
    print(f"wrote reviewable phrase candidates: {len(reviewable)}")


if __name__ == "__main__":
    main()
