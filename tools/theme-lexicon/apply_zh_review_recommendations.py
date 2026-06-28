"""Apply SubAgent alias review recommendations to review decisions.

The default target language remains Chinese for backward compatibility with
the existing L3 zh review workflow.
"""

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


def _key(row: dict[str, Any], *, default_lang: str | None = None) -> tuple[str, str, str]:
    return str(row.get("lang") or default_lang or ""), str(row.get("concept_id") or ""), str(row.get("alias") or "")


def apply_zh_review_recommendations(
    *,
    review_decisions_path: Path,
    recommendations_path: Path,
    output_path: Path | None = None,
    accept_missing: bool = False,
    lang: str = "zh",
    include_decisions: set[str] | None = None,
) -> dict[str, Any]:
    if lang not in {"en", "zh"}:
        raise ValueError(f"Unsupported review language: {lang}")
    if accept_missing and lang != "zh":
        raise ValueError("accept_missing is only supported for zh review")
    include_decisions = set(include_decisions or {"needs_review"})
    unsupported_decisions = include_decisions - {"needs_review", "blocked", "accept"}
    if unsupported_decisions:
        raise ValueError(f"Unsupported include_decisions: {sorted(unsupported_decisions)}")
    if accept_missing and include_decisions != {"needs_review"}:
        raise ValueError("accept_missing cannot be combined with blocked review rows")
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
        explicit[_key(item, default_lang=lang)] = item

    rows = _read_jsonl(review_decisions_path)
    counts = {"accept": 0, "reject": 0, "blocked": 0, "unchanged": 0}
    applied_at = datetime.now(timezone.utc).date().isoformat()

    for row in rows:
        if row.get("lang") != lang or row.get("decision") not in include_decisions:
            counts["unchanged"] += 1
            continue
        recommendation = explicit.get(_key(row, default_lang=lang))
        if recommendation is None:
            if not accept_missing:
                counts["unchanged"] += 1
                continue
            decision = "accept"
            reason = f"SubAgent review did not flag this high-confidence {lang} alias"
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
        "schema_version": f"theme_{lang}_review_apply.v1",
        "review_decisions": str(output_path.resolve()),
        "recommendations": str(recommendations_path.resolve()),
        "accept_missing": accept_missing,
        "include_decisions": sorted(include_decisions),
        "lang": lang,
        "written": written,
        **counts,
    }
    manifest_path = output_path.parent / f"{lang}_review_apply_manifest.json"
    summary["manifest"] = str(manifest_path)
    manifest_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-decisions", type=Path, default=Path("lexicons/review/review_decisions.jsonl"))
    parser.add_argument("--recommendations", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--lang", choices=("en", "zh"), default="zh", help="Review decision language to update.")
    parser.add_argument(
        "--include-decision",
        action="append",
        choices=("needs_review", "blocked", "accept"),
        dest="include_decisions",
        help="Decision state eligible for explicit recommendations. Defaults to needs_review; repeat to include blocked.",
    )
    parser.add_argument(
        "--accept-missing",
        action="store_true",
        help="Legacy zh-only mode: accept zh needs_review rows missing from recommendations.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = apply_zh_review_recommendations(
        review_decisions_path=args.review_decisions,
        recommendations_path=args.recommendations,
        output_path=args.output,
        accept_missing=args.accept_missing,
        lang=args.lang,
        include_decisions=set(args.include_decisions or {"needs_review"}),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
