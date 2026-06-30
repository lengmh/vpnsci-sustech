"""Validate and normalize theme concept curation decisions.

This C2 helper does not change runtime materialization by itself.  It validates
the versioned curation source and writes a compact overlay that later C3 runtime
materialization can consume.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INDEX_PATH = REPO_ROOT / "vpnsci_sustech" / "data" / "theme_concept_alias_index.json"
DEFAULT_CURRATION_DECISIONS_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "concept_curation_decisions.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "lexicons" / "builds" / "concept_curation_overlay.json"

DECISIONS_SCHEMA_VERSION = "theme_concept_curation_decisions.v1"
OVERLAY_SCHEMA_VERSION = "theme_concept_curation_overlay.v1"
VALID_DECISIONS = {"canonical", "redirect", "suppressed", "display_only"}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _active_decisions(raw_decisions: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    active: list[dict[str, Any]] = []
    for row in raw_decisions:
        if not isinstance(row, dict):
            raise ValueError("Curation decisions must be objects")
        if row.get("active") is False:
            continue
        active.append(row)
    return active


def _load_concepts(index_path: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(index_path)
    concepts = payload.get("concepts") or {}
    if not isinstance(concepts, dict):
        raise ValueError("Runtime index concepts must be an object")
    return concepts


def _validate_required_metadata(row: dict[str, Any], concept_id: str) -> None:
    for field in ("category", "reason", "reviewer", "decided_at"):
        if not _clean(row.get(field)):
            raise ValueError(f"Curation decision for {concept_id} is missing required field: {field}")


def _detect_redirect_cycle(start: str, redirects: dict[str, str]) -> list[str] | None:
    seen: list[str] = []
    current = start
    while current in redirects:
        if current in seen:
            return [*seen[seen.index(current) :], current]
        seen.append(current)
        current = redirects[current]
    return None


def _normalize_decision(row: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "concept_id": _clean(row.get("concept_id")),
        "decision": _clean(row.get("decision")),
        "category": _clean(row.get("category")),
        "reason": _clean(row.get("reason")),
        "reviewer": _clean(row.get("reviewer")),
        "decided_at": _clean(row.get("decided_at")),
    }
    target = _clean(row.get("target_concept_id"))
    if target:
        normalized["target_concept_id"] = target
    topic_disposition = _clean(row.get("topic_label_disposition"))
    if topic_disposition:
        normalized["topic_label_disposition"] = topic_disposition
    return normalized


def apply_concept_curation(
    *,
    index_path: Path = DEFAULT_INDEX_PATH,
    curation_decisions_path: Path = DEFAULT_CURRATION_DECISIONS_PATH,
    output_path: Path | None = DEFAULT_OUTPUT_PATH,
) -> dict[str, Any]:
    index_path = Path(index_path)
    curation_decisions_path = Path(curation_decisions_path)
    output_path = Path(output_path) if output_path is not None else None

    concepts = _load_concepts(index_path)
    payload = _read_json(curation_decisions_path)
    schema_version = payload.get("schema_version")
    if schema_version != DECISIONS_SCHEMA_VERSION:
        raise ValueError(f"Unsupported curation schema_version: {schema_version}")
    raw_decisions = payload.get("decisions") or []
    if not isinstance(raw_decisions, list):
        raise ValueError("Curation decisions must be a list")

    active = _active_decisions(raw_decisions)
    seen_concepts: set[str] = set()
    normalized_decisions: list[dict[str, Any]] = []
    redirects: dict[str, str] = {}
    suppressed: set[str] = set()
    display_only: set[str] = set()
    canonical: set[str] = set()
    counts: Counter[str] = Counter()

    for row in active:
        concept_id = _clean(row.get("concept_id"))
        decision = _clean(row.get("decision"))
        if decision not in VALID_DECISIONS:
            raise ValueError(f"Unsupported curation decision for {concept_id}: {decision}")
        if concept_id not in concepts:
            raise ValueError(f"Curation concept does not exist: {concept_id}")
        if concept_id in seen_concepts:
            raise ValueError(f"Concept has multiple active curation decisions: {concept_id}")
        seen_concepts.add(concept_id)
        _validate_required_metadata(row, concept_id)

        if decision == "redirect":
            target_id = _clean(row.get("target_concept_id"))
            if not target_id:
                raise ValueError(f"Redirect decision missing target_concept_id: {concept_id}")
            if target_id == concept_id:
                raise ValueError(f"Concept cannot redirect to itself: {concept_id}")
            if target_id not in concepts:
                raise ValueError(f"redirect target does not exist: {target_id}")
            redirects[concept_id] = target_id
        elif decision == "suppressed":
            suppressed.add(concept_id)
        elif decision == "display_only":
            display_only.add(concept_id)
        else:
            canonical.add(concept_id)

        normalized_decisions.append(_normalize_decision(row))
        counts[decision] += 1

    for source_id, target_id in redirects.items():
        if target_id in suppressed:
            raise ValueError(f"redirect target is suppressed: {source_id} -> {target_id}")
        cycle = _detect_redirect_cycle(source_id, redirects)
        if cycle:
            raise ValueError(f"redirect cycle detected: {' -> '.join(cycle)}")
        if target_id in redirects:
            raise ValueError(f"redirect target is also redirected: {source_id} -> {target_id} -> {redirects[target_id]}")

    overlay = {
        "schema_version": OVERLAY_SCHEMA_VERSION,
        "source": str(curation_decisions_path.resolve()),
        "canonical": sorted(canonical),
        "redirects": dict(sorted(redirects.items())),
        "suppressed": sorted(suppressed),
        "display_only": sorted(display_only),
        "decisions": sorted(normalized_decisions, key=lambda item: item["concept_id"]),
        "counts": dict(sorted(counts.items())),
    }
    if output_path is not None:
        _write_json(output_path, overlay)

    return {
        "schema_version": OVERLAY_SCHEMA_VERSION,
        "index_path": str(index_path.resolve()),
        "curation_decisions_path": str(curation_decisions_path.resolve()),
        "output_path": str(output_path.resolve()) if output_path is not None else None,
        "active_decisions": len(active),
        "counts": dict(sorted(counts.items())),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-path", type=Path, default=DEFAULT_INDEX_PATH)
    parser.add_argument("--curation-decisions", type=Path, default=DEFAULT_CURRATION_DECISIONS_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = apply_concept_curation(
        index_path=args.index_path,
        curation_decisions_path=args.curation_decisions,
        output_path=args.output,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
