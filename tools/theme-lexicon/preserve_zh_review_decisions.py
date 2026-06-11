"""Preserve prior accepted/rejected/blocked Chinese review decisions after revalidation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable


PRESERVED_DECISIONS = {"accept", "reject", "blocked"}
PRESERVED_FIELDS = {
    "decision",
    "review_tier",
    "reviewer",
    "reason",
    "decided_at",
    "subagent_recommendation",
}


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


def _key(row: dict[str, Any]) -> tuple[str, str, str]:
    return str(row.get("lang") or ""), str(row.get("concept_id") or ""), str(row.get("alias") or "")


def preserve_zh_review_decisions(
    *,
    prior_path: Path,
    current_path: Path,
    output_path: Path | None = None,
) -> dict[str, Any]:
    prior_path = Path(prior_path)
    current_path = Path(current_path)
    output_path = Path(output_path or current_path)

    prior_rows = _read_jsonl(prior_path)
    current_rows = _read_jsonl(current_path)
    prior_by_key = {
        _key(row): row
        for row in prior_rows
        if row.get("lang") == "zh" and row.get("decision") in PRESERVED_DECISIONS
    }

    preserved = 0
    for row in current_rows:
        prior = prior_by_key.get(_key(row))
        if not prior or row.get("lang") != "zh" or row.get("decision") != "needs_review":
            continue
        for field in PRESERVED_FIELDS:
            if field in prior:
                row[field] = prior[field]
        preserved += 1

    written = _write_jsonl(output_path, current_rows)
    summary = {
        "schema_version": "theme_zh_review_preserve.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prior": str(prior_path.resolve()),
        "current": str(output_path.resolve()),
        "written": written,
        "preserved": preserved,
    }
    manifest_path = output_path.parent / "zh_review_preserve_manifest.json"
    summary["manifest"] = str(manifest_path)
    manifest_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--current", type=Path, default=Path("lexicons/review/review_decisions.jsonl"))
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = preserve_zh_review_decisions(prior_path=args.prior, current_path=args.current, output_path=args.output)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
