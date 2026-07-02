from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import shutil
from typing import Any

from vpnsci_sustech.theme_clustering import (
    _concept_alias_key,
    _is_chinese_term,
    _is_noisy_theme_term,
    _is_valid_chinese_theme_candidate,
)


SCHEMA_VERSION = "theme_concept_ambiguous_alias_candidates.v1"
MANIFEST_SCHEMA_VERSION = "theme_concept_ambiguous_alias_manifest.v1"
BUILD_STATUS = "review_complete"
NORMALIZATION = "theme_concept_alias_normalization.v1"
ALLOWED_AUDIT_BUCKETS = {
    "needs_decision_candidates",
    "redirect_candidates",
    "singleton_gaps",
}
EXCLUDED_DECISIONS = {"display_only", "suppressed"}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if not path or not Path(path).exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
    return rows


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _active_excluded_concepts(curation_decisions_path: Path | None) -> set[str]:
    if not curation_decisions_path or not Path(curation_decisions_path).exists():
        return set()
    payload = _read_json(Path(curation_decisions_path))
    excluded: set[str] = set()
    for decision in payload.get("decisions") or []:
        if not isinstance(decision, dict):
            continue
        if decision.get("active") is False:
            continue
        if str(decision.get("decision") or "") in EXCLUDED_DECISIONS:
            concept_id = str(decision.get("concept_id") or "")
            if concept_id:
                excluded.add(concept_id)
    return excluded


def _audit_item_map(audit_path: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(audit_path)
    items: dict[str, dict[str, Any]] = {}
    for item in payload.get("items") or []:
        if not isinstance(item, dict):
            continue
        concept_id = str(item.get("concept_id") or "")
        if concept_id:
            items[concept_id] = item
    return items


def _allowed_audit_item(item: dict[str, Any], excluded_concepts: set[str]) -> bool:
    concept_id = str(item.get("concept_id") or "")
    if not concept_id or concept_id in excluded_concepts:
        return False
    bucket = str(item.get("primary_bucket") or "")
    if bucket not in ALLOWED_AUDIT_BUCKETS:
        return False
    categories = {str(value) for value in item.get("categories") or []}
    if any("topic_label" in value or "suppressed" in value or "broad" in value for value in categories):
        return False
    return True


def _review_rejects(rows: list[dict[str, Any]]) -> set[tuple[str, str, str]]:
    rejects: set[tuple[str, str, str]] = set()
    for row in rows:
        if str(row.get("decision") or "") != "reject":
            continue
        lang = str(row.get("lang") or ("zh" if _is_chinese_term(str(row.get("alias") or "")) else "en"))
        concept_id = str(row.get("concept_id") or "")
        alias = str(row.get("alias") or "")
        if concept_id and alias:
            rejects.add((lang, concept_id, alias))
    return rejects


def _blocked_rows_for_audit_item(
    item: dict[str, Any],
    review_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    concept_id = str(item.get("concept_id") or "")
    rows: list[dict[str, Any]] = []
    for sample in item.get("sample_zh_review_rows") or []:
        if isinstance(sample, dict) and str(sample.get("decision") or "") == "blocked":
            row = dict(sample)
            row.setdefault("lang", "zh" if _is_chinese_term(str(row.get("alias") or "")) else "en")
            row.setdefault("concept_id", concept_id)
            rows.append(row)
    for row in review_rows:
        if str(row.get("concept_id") or "") != concept_id:
            continue
        if str(row.get("decision") or "") != "blocked":
            continue
        rows.append(row)

    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        alias = str(row.get("alias") or "").strip()
        lang = str(row.get("lang") or ("zh" if _is_chinese_term(alias) else "en"))
        key = (lang, alias)
        if not alias or key in seen:
            continue
        seen.add(key)
        row = dict(row)
        row["alias"] = alias
        row["lang"] = lang
        deduped.append(row)
    return deduped


def _alias_allowed(lang: str, alias: str) -> bool:
    if not alias:
        return False
    if lang == "zh":
        if alias.endswith("主题"):
            return False
        if _is_noisy_theme_term(alias):
            return False
        return _is_valid_chinese_theme_candidate(alias)
    return len(alias.strip()) >= 2


def _risk_tags(item: dict[str, Any], row: dict[str, Any]) -> list[str]:
    tags = {"needs_context"}
    bucket = str(item.get("primary_bucket") or "")
    categories = [str(value) for value in item.get("categories") or []]
    reason = str(row.get("reason") or "").casefold()
    if bucket == "redirect_candidates" or "collision" in reason or any("collision" in value for value in categories):
        tags.add("collision_alias")
    if "semantic" in reason or any("semantic" in value for value in categories):
        tags.add("semantic_neighbor")
    if any("acronym" in value or "short" in value for value in categories):
        tags.add("acronym_or_short_label")
    if any("variant" in value or "plural" in value for value in categories):
        tags.add("source_variant")
    return sorted(tags)


def _candidate_type(item: dict[str, Any]) -> str:
    bucket = str(item.get("primary_bucket") or "")
    if bucket == "redirect_candidates":
        return "collision_alias"
    if bucket == "singleton_gaps":
        return "blocked_singleton_alias"
    return "needs_decision_alias"


def _concept_metadata(concept_id: str, item: dict[str, Any], compact_concepts: dict[str, Any]) -> dict[str, Any]:
    concept = compact_concepts.get(concept_id)
    if isinstance(concept, dict):
        canonical = concept.get("canonical") if isinstance(concept.get("canonical"), dict) else {}
        return {
            "canonical": {
                "en": str(canonical.get("en") or item.get("canonical_en") or ""),
                "zh": str(canonical.get("zh") or ""),
            },
            "domains": [str(value) for value in concept.get("domains") or item.get("domains") or []],
            "parents": [str(value) for value in concept.get("parents") or []],
            "specificity": int(concept.get("specificity") or item.get("specificity") or 0),
        }
    return {
        "canonical": {"en": str(item.get("canonical_en") or ""), "zh": str(item.get("canonical_zh") or "")},
        "domains": [str(value) for value in item.get("domains") or []],
        "parents": [str(value) for value in item.get("parents") or []],
        "specificity": int(item.get("specificity") or 0),
    }


def _candidate_record(
    *,
    concept_id: str,
    item: dict[str, Any],
    row: dict[str, Any],
    compact_concepts: dict[str, Any],
) -> dict[str, Any]:
    metadata = _concept_metadata(concept_id, item, compact_concepts)
    lang = str(row.get("lang") or "zh")
    alias = str(row.get("alias") or "")
    return {
        "concept_id": concept_id,
        "canonical": metadata["canonical"],
        "domains": metadata["domains"],
        "parents": metadata["parents"],
        "specificity": metadata["specificity"],
        "candidate_type": _candidate_type(item),
        "risk_tags": _risk_tags(item, row),
        "evidence_aliases": [{"lang": lang, "alias": alias}],
        "source_concept_id": concept_id,
        "target_hint": item.get("english_alias_target") or item.get("base_concept_target"),
        "reason": str(row.get("reason") or "blocked candidate requires paper context"),
    }


def build_ambiguous_alias_candidates(
    *,
    audit_path: Path,
    review_decisions_path: Path | None,
    alias_index_path: Path,
    curation_decisions_path: Path | None = None,
    output_path: Path,
    manifest_path: Path | None = None,
    tool_output_path: Path | None = None,
    tool_manifest_path: Path | None = None,
) -> dict[str, Any]:
    audit_items = _audit_item_map(Path(audit_path))
    review_rows = _read_jsonl(review_decisions_path)
    rejected = _review_rejects(review_rows)
    excluded = _active_excluded_concepts(curation_decisions_path)
    alias_payload = _read_json(Path(alias_index_path))
    deterministic_aliases = {str(key) for key in (alias_payload.get("aliases") or {})}
    compact_concepts = {
        str(concept_id): concept
        for concept_id, concept in (alias_payload.get("concepts") or {}).items()
        if isinstance(concept, dict)
    }

    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for concept_id, item in audit_items.items():
        if not _allowed_audit_item(item, excluded):
            continue
        for row in _blocked_rows_for_audit_item(item, review_rows):
            alias = str(row.get("alias") or "").strip()
            lang = str(row.get("lang") or ("zh" if _is_chinese_term(alias) else "en"))
            if (lang, concept_id, alias) in rejected or not _alias_allowed(lang, alias):
                continue
            alias_key = _concept_alias_key(alias)
            if alias_key in deterministic_aliases:
                continue
            candidates[alias_key].append(
                _candidate_record(
                    concept_id=concept_id,
                    item=item,
                    row=row,
                    compact_concepts=compact_concepts,
                )
            )

    normalized_candidates: dict[str, list[dict[str, Any]]] = {}
    for alias_key, records in sorted(candidates.items()):
        deduped: dict[str, dict[str, Any]] = {}
        for record in records:
            deduped.setdefault(str(record["concept_id"]), record)
        if not deduped:
            continue
        normalized_candidates[alias_key] = sorted(
            deduped.values(),
            key=lambda record: (
                -int(record.get("specificity") or 0),
                str((record.get("canonical") or {}).get("en") or ""),
                str(record.get("concept_id") or ""),
            ),
        )

    concept_ids = {
        str(candidate.get("concept_id") or "")
        for records in normalized_candidates.values()
        for candidate in records
        if candidate.get("concept_id")
    }
    lang_counts = Counter(alias_key.split(":", 1)[0] for alias_key in normalized_candidates)
    risk_counts = Counter(
        tag
        for records in normalized_candidates.values()
        for candidate in records
        for tag in candidate.get("risk_tags") or []
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "build_status": BUILD_STATUS,
        "normalization": NORMALIZATION,
        "candidates": normalized_candidates,
    }
    summary = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "build_status": BUILD_STATUS,
        "candidate_aliases": len(normalized_candidates),
        "candidate_aliases_by_lang": dict(sorted(lang_counts.items())),
        "candidate_concepts": len(concept_ids),
        "candidate_resolvable_concepts": len(concept_ids),
        "risk_tag_counts": dict(sorted(risk_counts.items())),
        "coverage": {
            "definition": "deterministic_covered + candidate_resolvable_covered; deterministic runtime coverage is unchanged",
            "candidate_resolvable_concepts": len(concept_ids),
            "candidate_resolvable_aliases": len(normalized_candidates),
        },
    }

    _write_json(output_path, payload)
    if manifest_path:
        _write_json(manifest_path, summary)
    if tool_output_path:
        Path(tool_output_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(output_path, tool_output_path)
    if tool_manifest_path and manifest_path:
        Path(tool_manifest_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(manifest_path, tool_manifest_path)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--review-decisions", type=Path)
    parser.add_argument("--alias-index", required=True, type=Path)
    parser.add_argument("--curation-decisions", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--tool-output", type=Path)
    parser.add_argument("--tool-manifest", type=Path)
    args = parser.parse_args()
    summary = build_ambiguous_alias_candidates(
        audit_path=args.audit,
        review_decisions_path=args.review_decisions,
        alias_index_path=args.alias_index,
        curation_decisions_path=args.curation_decisions,
        output_path=args.output,
        manifest_path=args.manifest,
        tool_output_path=args.tool_output,
        tool_manifest_path=args.tool_manifest,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
