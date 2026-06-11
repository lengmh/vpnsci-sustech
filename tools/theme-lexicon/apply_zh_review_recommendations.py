"""Apply SubAgent Chinese alias review recommendations to review decisions."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable


VALID_RECOMMENDATIONS = {"accept", "reject", "blocked"}


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


def _key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row.get("concept_id") or ""), str(row.get("alias") or "")


def apply_zh_review_recommendations(
    *,
    review_decisions_path: Path,
    recommendations_path: Path,
    output_path: Path | None = None,
    accept_missing: bool = False,
) -> dict[str, Any]:
    review_decisions_path = Path(review_decisions_path)
    recommendations_path = Path(recommendations_path)
    output_path = Path(output_path or review_decisions_path)

    payload = json.loads(recommendations_path.read_text(encoding="utf-8"))
    explicit = {}
    for item in payload.get("recommendations") or []:
        if not isinstance(item, dict):
            continue
        recommendation = str(item.get("recommendation") or "")
        if recommendation not in VALID_RECOMMENDATIONS:
            raise ValueError(f"Invalid recommendation: {recommendation}")
        explicit[_key(item)] = item

    rows = _read_jsonl(review_decisions_path)
    counts = {"accept": 0, "reject": 0, "blocked": 0, "unchanged": 0}
    applied_at = datetime.now(timezone.utc).date().isoformat()

    for row in rows:
        if row.get("lang") != "zh" or row.get("decision") != "needs_review":
            counts["unchanged"] += 1
            continue
        recommendation = explicit.get(_key(row))
        if recommendation is None:
            if not accept_missing:
                counts["unchanged"] += 1
                continue
            decision = "accept"
            reason = "SubAgent review did not flag this high-confidence Chinese alias"
            merge_duplicate_concepts = False
        else:
            decision = str(recommendation["recommendation"])
            reason = str(recommendation.get("reason") or "SubAgent review recommendation")
            merge_duplicate_concepts = bool(recommendation.get("merge_duplicate_concepts"))
        row["decision"] = decision
        row["reviewer"] = f"subagent-recommended+main-agent-accepted"
        row["decided_at"] = applied_at
        row["reason"] = reason
        row["subagent_recommendation"] = {
            "decision": decision,
            "reason": reason,
            "merge_duplicate_concepts": merge_duplicate_concepts,
        }
        if decision == "accept":
            row["review_tier"] = "review_accept"
        elif decision == "reject":
            row["review_tier"] = "review_reject"
        else:
            row["review_tier"] = "review_blocked"
        counts[decision] += 1

    written = _write_jsonl(output_path, rows)
    summary = {
        "schema_version": "theme_zh_review_apply.v1",
        "review_decisions": str(output_path.resolve()),
        "recommendations": str(recommendations_path.resolve()),
        "accept_missing": accept_missing,
        "written": written,
        **counts,
    }
    manifest_path = output_path.parent / "zh_review_apply_manifest.json"
    summary["manifest"] = str(manifest_path)
    manifest_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-decisions", type=Path, default=Path("lexicons/review/review_decisions.jsonl"))
    parser.add_argument("--recommendations", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--accept-missing",
        action="store_true",
        help="Legacy mode: accept zh needs_review rows missing from recommendations.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = apply_zh_review_recommendations(
        review_decisions_path=args.review_decisions,
        recommendations_path=args.recommendations,
        output_path=args.output,
        accept_missing=args.accept_missing,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
