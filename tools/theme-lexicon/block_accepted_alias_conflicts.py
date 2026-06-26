"""Block accepted aliases that still collide across multiple concept IDs.

This is a conservative L4/L5 guard.  If a normalized accepted alias maps to
more than one concept, the current pipeline has no safe runtime merge target.
Those rows are therefore moved from ``accept`` to ``blocked`` until a separate
concept-merge decision resolves the duplicate concepts.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Iterable


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_alias(value: str) -> str:
    text = _clean_text(value).casefold()
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        text = re.sub(r"(?<=[\u4e00-\u9fff])(?=[A-Za-z0-9])", " ", text)
        text = re.sub(r"(?<=[A-Za-z0-9])(?=[\u4e00-\u9fff])", " ", text)
    text = text.replace("∞", " infinity ")
    text = text.replace("&", " and ")
    text = re.sub(r"[\-_/]+", " ", text)
    text = re.sub(r"[^\w\s\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    materialized = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in materialized:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(materialized)


def block_accepted_alias_conflicts(
    *,
    review_decisions_path: Path,
    output_path: Path | None = None,
) -> dict[str, Any]:
    review_decisions_path = Path(review_decisions_path)
    output_path = Path(output_path or review_decisions_path)
    rows = _read_jsonl(review_decisions_path)

    alias_to_concepts: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in rows:
        if row.get("decision") != "accept":
            continue
        lang = _clean_text(row.get("lang"))
        if lang not in {"en", "zh"}:
            continue
        concept_id = _clean_text(row.get("concept_id"))
        alias = _clean_text(row.get("alias"))
        if concept_id and alias:
            alias_to_concepts[(lang, _normalize_alias(alias))].add(concept_id)

    conflicted_keys = {key for key, concept_ids in alias_to_concepts.items() if len(concept_ids) > 1}
    conflict_groups = [
        {
            "lang": lang,
            "alias_key": alias_key,
            "concept_ids": sorted(alias_to_concepts[(lang, alias_key)]),
        }
        for lang, alias_key in sorted(conflicted_keys)
    ]

    decided_at = datetime.now(timezone.utc).date().isoformat()
    counts: Counter[str] = Counter()
    for row in rows:
        if row.get("decision") != "accept":
            counts["unchanged"] += 1
            continue
        lang = _clean_text(row.get("lang"))
        alias = _clean_text(row.get("alias"))
        if (lang, _normalize_alias(alias)) not in conflicted_keys:
            counts["unchanged"] += 1
            continue

        row["decision"] = "blocked"
        row["review_tier"] = "review_blocked"
        row["reviewer"] = "main-agent-accepted-collision-guard"
        row["decided_at"] = decided_at
        row["reason"] = (
            "accepted alias collision blocked until duplicate concept merge "
            "or single runtime target is explicitly resolved"
        )
        counts["blocked"] += 1

    written = _write_jsonl(output_path, rows)
    summary = {
        "schema_version": "theme_accepted_alias_collision_guard.v1",
        "review_decisions": str(output_path.resolve()),
        "accepted_conflict_groups": len(conflict_groups),
        "blocked": counts["blocked"],
        "unchanged": counts["unchanged"],
        "written": written,
        "conflicts": conflict_groups,
    }
    manifest_path = output_path.parent / "accepted_alias_collision_guard_manifest.json"
    summary["manifest"] = str(manifest_path)
    manifest_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-decisions", type=Path, default=Path("lexicons/review/review_decisions.jsonl"))
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = block_accepted_alias_conflicts(
        review_decisions_path=args.review_decisions,
        output_path=args.output,
    )
    printable = {key: value for key, value in summary.items() if key != "conflicts"}
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
