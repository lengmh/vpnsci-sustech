"""Materialize reviewed concept aliases into tracked runtime overlay files.

This is the L5 offline promotion step. It reads ignored construction artifacts
under ``lexicons/`` and writes only accepted aliases plus minimal provenance to
the package data copy and the bundled paper-search-pro asset copy.

The script never reads raw source dumps, candidate rationale payloads, report
artifacts, or search artifacts.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
from typing import Any, Iterable


DEFAULT_OUTPUTS = (
    Path("vpnsci_sustech/data/theme_concept_aliases.json"),
    Path("tools/paper-search-pro/assets/theme_concept_aliases.json"),
)


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_alias(value: str) -> str:
    text = _clean_text(value).casefold()
    text = text.replace("&", " and ")
    text = re.sub(r"[\-_/]+", " ", text)
    text = re.sub(r"[^\w\s\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _unique_text(values: Iterable[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_text(value)
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _minimal_source_ref(ref: dict[str, Any]) -> dict[str, str]:
    out = {
        "source": _clean_text(ref.get("source")),
        "label": _clean_text(ref.get("label")),
    }
    source_id = _clean_text(ref.get("source_id"))
    if source_id:
        out["source_id"] = source_id
    return {key: value for key, value in out.items() if value}


def _concept_sort_key(concept: dict[str, Any]) -> tuple[str, str]:
    canonical = concept.get("canonical") or {}
    return str(concept.get("concept_id") or ""), str(canonical.get("en") or "")


def _load_concepts(path: Path) -> dict[str, dict[str, Any]]:
    concepts: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        concept_id = _clean_text(row.get("concept_id"))
        if concept_id:
            concepts[concept_id] = row
    return concepts


def _load_accepted_aliases(path: Path) -> tuple[dict[str, dict[str, list[str]]], dict[str, int], list[dict[str, Any]]]:
    summary: Counter[str] = Counter()
    alias_rows: list[dict[str, str]] = []
    for row in _read_jsonl(path):
        lang = _clean_text(row.get("lang"))
        decision = _clean_text(row.get("decision"))
        summary[f"{lang}:{decision}"] += 1
        if decision != "accept" or lang not in {"en", "zh"}:
            continue
        concept_id = _clean_text(row.get("concept_id"))
        alias = _clean_text(row.get("alias"))
        if concept_id and alias:
            alias_rows.append({"concept_id": concept_id, "lang": lang, "alias": alias})

    alias_to_concepts: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in alias_rows:
        alias_to_concepts[(row["lang"], _normalize_alias(row["alias"]))].add(row["concept_id"])
    conflicted_keys = {key for key, concept_ids in alias_to_concepts.items() if len(concept_ids) > 1}
    skipped_conflicts = [
        {
            "lang": lang,
            "alias_key": alias_key,
            "concept_ids": sorted(alias_to_concepts[(lang, alias_key)]),
        }
        for lang, alias_key in sorted(conflicted_keys)
    ]

    accepted: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"en": [], "zh": []})
    for row in alias_rows:
        key = (row["lang"], _normalize_alias(row["alias"]))
        if key in conflicted_keys:
            continue
        accepted[row["concept_id"]][row["lang"]].append(row["alias"])
    return accepted, dict(sorted(summary.items())), skipped_conflicts


def _overlay_entry(concept: dict[str, Any], aliases: dict[str, list[str]]) -> dict[str, Any] | None:
    aliases_en = _unique_text(aliases.get("en") or [])
    aliases_zh = _unique_text(aliases.get("zh") or [])
    if not aliases_en and not aliases_zh:
        return None

    canonical_en = aliases_en[0] if aliases_en else None
    canonical_zh = aliases_zh[0] if aliases_zh else None
    source_refs = [
        ref
        for ref in (_minimal_source_ref(item) for item in (concept.get("source_refs") or []) if isinstance(item, dict))
        if ref.get("source") and ref.get("label")
    ]

    return {
        "concept_id": _clean_text(concept.get("concept_id")),
        "canonical": {
            "en": canonical_en,
            "zh": canonical_zh,
        },
        "aliases": {
            "en": aliases_en,
            "zh": aliases_zh,
        },
        "domains": _unique_text(concept.get("domains") or []),
        "parents": _unique_text(concept.get("parents") or []),
        "specificity": int(concept.get("specificity") or 0),
        "source_refs": source_refs,
        "review_status": "accepted",
        "confidence": "curated",
    }


def materialize_runtime_overlay(
    *,
    concepts_path: Path,
    review_decisions_path: Path,
    outputs: Iterable[Path] = DEFAULT_OUTPUTS,
) -> dict[str, Any]:
    concepts = _load_concepts(Path(concepts_path))
    accepted, review_summary, skipped_conflicts = _load_accepted_aliases(Path(review_decisions_path))

    entries: list[dict[str, Any]] = []
    missing_concepts: list[str] = []
    for concept_id, aliases in sorted(accepted.items()):
        concept = concepts.get(concept_id)
        if not concept:
            missing_concepts.append(concept_id)
            continue
        entry = _overlay_entry(concept, aliases)
        if entry:
            entries.append(entry)
    entries.sort(key=_concept_sort_key)

    pending_review = sum(
        count
        for key, count in review_summary.items()
        if key.endswith(":needs_review")
    )
    payload = {
        "schema_version": "theme_concept_aliases.v1",
        "build_status": "partial_review_pending" if pending_review else "review_complete",
        "review_decision_row_summary": review_summary,
        "skipped_accepted_alias_conflict_count": len(skipped_conflicts),
        "concept_aliases": entries,
    }

    written: list[str] = []
    for output in outputs:
        output = Path(output)
        _write_json(output, payload)
        written.append(str(output))

    return {
        "schema_version": "theme_concept_aliases_materialize.v1",
        "build_status": payload["build_status"],
        "concepts_loaded": len(concepts),
        "concept_aliases": len(entries),
        "missing_concepts": missing_concepts,
        "review_decision_row_summary": review_summary,
        "skipped_accepted_alias_conflicts": len(skipped_conflicts),
        "outputs": written,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concepts", type=Path, default=Path("lexicons/builds/merged_en_concept_candidates.jsonl"))
    parser.add_argument("--review-decisions", type=Path, default=Path("lexicons/review/review_decisions.jsonl"))
    parser.add_argument("--output", action="append", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = materialize_runtime_overlay(
        concepts_path=args.concepts,
        review_decisions_path=args.review_decisions,
        outputs=args.output or DEFAULT_OUTPUTS,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
