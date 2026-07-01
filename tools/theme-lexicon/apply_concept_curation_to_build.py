"""Apply reviewed concept curation to an English concept build snapshot.

This is a build-level working-view helper.  It does not replace runtime
materialization yet: accepted alias review rows may still reference redirected
source concept IDs, so runtime materialization should keep using the curation
overlay until the review-decision layer is remapped too.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
import json
from pathlib import Path
from typing import Any


DEFAULT_CONCEPTS_PATH = Path("lexicons/builds/merged_en_concept_candidates.jsonl")
DEFAULT_CURATION_OVERLAY_PATH = Path("lexicons/builds/concept_curation_overlay.json")
DEFAULT_OUTPUT_PATH = Path("lexicons/builds/curated_en_concept_candidates.jsonl")
DEFAULT_MANIFEST_PATH = Path("lexicons/builds/curated_en_concept_build_manifest.json")

OVERLAY_SCHEMA_VERSION = "theme_concept_curation_overlay.v1"
SUMMARY_SCHEMA_VERSION = "theme_en_concept_build_curation.v1"


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
    ordered = sorted(rows, key=lambda row: (_clean(row.get("concept_id")), _clean((row.get("canonical") or {}).get("en"))))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in ordered:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(ordered)


def _unique_text(values: Iterable[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean(value)
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _dedupe_refs(refs: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for ref in refs:
        clean = {str(key): str(value) for key, value in (ref or {}).items() if value is not None and str(value)}
        key = (clean.get("source", ""), clean.get("source_id", ""), clean.get("label", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(clean)
    return out


def _load_concepts(path: Path) -> dict[str, dict[str, Any]]:
    concepts: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        concept_id = _clean(row.get("concept_id"))
        if concept_id:
            concepts[concept_id] = row
    return concepts


def _load_overlay(path: Path) -> dict[str, Any]:
    overlay = _read_json(path)
    schema_version = overlay.get("schema_version")
    if schema_version != OVERLAY_SCHEMA_VERSION:
        raise ValueError(f"Unsupported curation overlay schema_version: {schema_version}")
    return overlay


def _aliases(row: dict[str, Any], lang: str) -> list[str]:
    aliases = row.setdefault("aliases", {})
    if not isinstance(aliases, dict):
        aliases = {}
        row["aliases"] = aliases
    values = aliases.setdefault(lang, [])
    if not isinstance(values, list):
        values = []
        aliases[lang] = values
    return values


def _merge_source_into_target(source: dict[str, Any], target: dict[str, Any]) -> None:
    for lang in ("en", "zh"):
        _aliases(target, lang)[:] = _unique_text([*_aliases(target, lang), *_aliases(source, lang)])
    target["source_refs"] = _dedupe_refs([*(target.get("source_refs") or []), *(source.get("source_refs") or [])])
    target["domains"] = sorted(set(_unique_text([*(target.get("domains") or []), *(source.get("domains") or [])])))
    target["parents"] = sorted(set(_unique_text([*(target.get("parents") or []), *(source.get("parents") or [])])))
    target["specificity"] = max(int(target.get("specificity") or 0), int(source.get("specificity") or 0))


def _apply_canonical_overrides(concepts: dict[str, dict[str, Any]], overrides: dict[str, dict[str, str]]) -> None:
    for concept_id, override in overrides.items():
        concept = concepts.get(concept_id)
        if not concept:
            raise ValueError(f"canonical override concept does not exist: {concept_id}")
        canonical = concept.setdefault("canonical", {})
        if not isinstance(canonical, dict):
            canonical = {}
            concept["canonical"] = canonical
        if _clean(override.get("en")):
            canonical["en"] = _clean(override.get("en"))
        if _clean(override.get("zh")):
            canonical["zh"] = _clean(override.get("zh"))
        marker = {lang: _clean(value) for lang, value in override.items() if lang in {"en", "zh"} and _clean(value)}
        if marker:
            concept["curation_canonical_override"] = marker


def apply_concept_curation_to_build(
    *,
    concepts_path: Path = DEFAULT_CONCEPTS_PATH,
    curation_overlay_path: Path = DEFAULT_CURATION_OVERLAY_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    manifest_path: Path | None = DEFAULT_MANIFEST_PATH,
) -> dict[str, Any]:
    concepts_path = Path(concepts_path)
    curation_overlay_path = Path(curation_overlay_path)
    output_path = Path(output_path)
    manifest_path = Path(manifest_path) if manifest_path is not None else None

    concepts = _load_concepts(concepts_path)
    overlay = _load_overlay(curation_overlay_path)
    redirects: dict[str, str] = dict(overlay.get("redirects") or {})
    suppressed = set(overlay.get("suppressed") or [])
    display_only = set(overlay.get("display_only") or [])
    canonical_overrides: dict[str, dict[str, str]] = dict(overlay.get("canonical_overrides") or {})

    for concept_id in sorted(suppressed | display_only | set(redirects)):
        if concept_id not in concepts:
            raise ValueError(f"curation source concept does not exist in build snapshot: {concept_id}")
    for source_id, target_id in sorted(redirects.items()):
        if target_id not in concepts:
            raise ValueError(f"redirect target concept does not exist in build snapshot: {source_id} -> {target_id}")
        if target_id in suppressed or target_id in display_only:
            raise ValueError(f"redirect target is excluded from curated build: {source_id} -> {target_id}")
        _merge_source_into_target(concepts[source_id], concepts[target_id])

    _apply_canonical_overrides(concepts, canonical_overrides)

    excluded = set(redirects) | suppressed | display_only
    curated = [row for concept_id, row in concepts.items() if concept_id not in excluded]
    output_count = _write_jsonl(output_path, curated)
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "concepts_path": str(concepts_path.resolve()),
        "curation_overlay_path": str(curation_overlay_path.resolve()),
        "output_path": str(output_path.resolve()),
        "manifest_path": str(manifest_path.resolve()) if manifest_path else None,
        "input_concepts": len(concepts),
        "output_concepts": output_count,
        "redirected_concepts": len(redirects),
        "suppressed_concepts": len(suppressed),
        "display_only_concepts": len(display_only),
        "canonical_concepts": len(canonical_overrides),
        "retired_concepts": len(excluded),
        "redirects": dict(sorted(redirects.items())),
        "suppressed": sorted(suppressed),
        "display_only": sorted(display_only),
        "canonical_overrides": dict(sorted(canonical_overrides.items())),
    }
    if manifest_path:
        _write_json(manifest_path, summary)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concepts", type=Path, default=DEFAULT_CONCEPTS_PATH)
    parser.add_argument("--curation-overlay", type=Path, default=DEFAULT_CURATION_OVERLAY_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = apply_concept_curation_to_build(
        concepts_path=args.concepts,
        curation_overlay_path=args.curation_overlay,
        output_path=args.output,
        manifest_path=args.manifest,
    )
    printable = {
        key: value
        for key, value in summary.items()
        if key not in {"redirects", "suppressed", "display_only", "canonical_overrides"}
    }
    print(json.dumps(printable, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
