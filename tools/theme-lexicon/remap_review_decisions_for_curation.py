"""Remap alias review decisions after build-level concept curation.

Redirected source concept rows are rewritten to their curation target.  Rows for
suppressed/display-only concepts are dropped so a curated build snapshot can be
materialized without the runtime curation overlay.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Iterable


DEFAULT_REVIEW_DECISIONS_PATH = Path("lexicons/review/review_decisions.jsonl")
DEFAULT_CURATION_OVERLAY_PATH = Path("lexicons/builds/concept_curation_overlay.json")
DEFAULT_OUTPUT_PATH = Path("lexicons/review/review_decisions.curated.jsonl")
DEFAULT_MANIFEST_PATH = Path("lexicons/review/review_decisions.curated_manifest.json")

OVERLAY_SCHEMA_VERSION = "theme_concept_curation_overlay.v1"
SUMMARY_SCHEMA_VERSION = "theme_review_decision_curation_remap.v1"


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    ordered = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in ordered:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(ordered)


def _load_overlay(path: Path) -> dict[str, Any]:
    overlay = _read_json(path)
    schema_version = overlay.get("schema_version")
    if schema_version != OVERLAY_SCHEMA_VERSION:
        raise ValueError(f"Unsupported curation overlay schema_version: {schema_version}")
    return overlay


def _dedupe_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        _clean(row.get("concept_id")),
        _clean(row.get("lang")),
        _clean(row.get("alias")).casefold(),
        _clean(row.get("decision")),
    )


def remap_review_decisions_for_curation(
    *,
    review_decisions_path: Path = DEFAULT_REVIEW_DECISIONS_PATH,
    curation_overlay_path: Path = DEFAULT_CURATION_OVERLAY_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    manifest_path: Path | None = DEFAULT_MANIFEST_PATH,
) -> dict[str, Any]:
    review_decisions_path = Path(review_decisions_path)
    curation_overlay_path = Path(curation_overlay_path)
    output_path = Path(output_path)
    manifest_path = Path(manifest_path) if manifest_path is not None else None

    overlay = _load_overlay(curation_overlay_path)
    redirects: dict[str, str] = dict(overlay.get("redirects") or {})
    excluded = set(overlay.get("suppressed") or []) | set(overlay.get("display_only") or [])
    rows = _read_jsonl(review_decisions_path)

    retained_rows: list[dict[str, Any]] = []
    redirect_source_rows: list[dict[str, Any]] = []
    input_summary: Counter[str] = Counter()
    output_summary: Counter[str] = Counter()
    remapped_rows = 0
    dropped_excluded_rows = 0
    deduplicated_rows = 0
    seen: set[tuple[str, str, str, str]] = set()

    for row in rows:
        concept_id = _clean(row.get("concept_id"))
        lang = _clean(row.get("lang"))
        decision = _clean(row.get("decision"))
        input_summary[f"{lang}:{decision}"] += 1

        if concept_id in excluded:
            dropped_excluded_rows += 1
            continue

        target_id = redirects.get(concept_id)
        if target_id:
            out = dict(row)
            out["concept_id"] = target_id
            out["curation_source_concept_id"] = concept_id
            out["curation_redirect_target_id"] = target_id
            remapped_rows += 1
            redirect_source_rows.append(out)
            continue

        retained_rows.append(dict(row))

    remapped: list[dict[str, Any]] = []
    for out in [*retained_rows, *redirect_source_rows]:
        key = _dedupe_key(out)
        if key in seen:
            deduplicated_rows += 1
            continue
        seen.add(key)
        remapped.append(out)
        output_summary[f"{_clean(out.get('lang'))}:{_clean(out.get('decision'))}"] += 1

    output_count = _write_jsonl(output_path, remapped)
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "review_decisions_path": str(review_decisions_path.resolve()),
        "curation_overlay_path": str(curation_overlay_path.resolve()),
        "output_path": str(output_path.resolve()),
        "manifest_path": str(manifest_path.resolve()) if manifest_path else None,
        "input_rows": len(rows),
        "output_rows": output_count,
        "remapped_rows": remapped_rows,
        "dropped_excluded_rows": dropped_excluded_rows,
        "deduplicated_rows": deduplicated_rows,
        "redirected_concepts": len(redirects),
        "excluded_concepts": len(excluded),
        "input_summary": dict(sorted(input_summary.items())),
        "output_summary": dict(sorted(output_summary.items())),
    }
    if manifest_path:
        _write_json(manifest_path, summary)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-decisions", type=Path, default=DEFAULT_REVIEW_DECISIONS_PATH)
    parser.add_argument("--curation-overlay", type=Path, default=DEFAULT_CURATION_OVERLAY_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = remap_review_decisions_for_curation(
        review_decisions_path=args.review_decisions,
        curation_overlay_path=args.curation_overlay,
        output_path=args.output,
        manifest_path=args.manifest,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
