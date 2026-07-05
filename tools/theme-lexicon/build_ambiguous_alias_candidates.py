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
CONTEXT_SEED_SCHEMA_VERSION = "theme_concept_contextual_alias_seeds.v1"
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


def _active_curation_metadata(
    curation_decisions_path: Path | None,
) -> tuple[set[str], dict[str, dict[str, str]], set[str]]:
    if not curation_decisions_path or not Path(curation_decisions_path).exists():
        return set(), {}, set()
    payload = _read_json(Path(curation_decisions_path))
    excluded: set[str] = set()
    canonical_overrides: dict[str, dict[str, str]] = {}
    redirect_targets: set[str] = set()
    for decision in payload.get("decisions") or []:
        if not isinstance(decision, dict):
            continue
        if decision.get("active") is False:
            continue
        concept_id = str(decision.get("concept_id") or "")
        if not concept_id:
            continue
        if str(decision.get("decision") or "") in EXCLUDED_DECISIONS:
            excluded.add(concept_id)
        if str(decision.get("decision") or "") == "redirect":
            target_concept_id = str(decision.get("target_concept_id") or "").strip()
            if target_concept_id:
                redirect_targets.add(target_concept_id)
        if str(decision.get("decision") or "") == "canonical":
            override: dict[str, str] = {}
            canonical_en = str(decision.get("canonical_en") or "").strip()
            canonical_zh = str(decision.get("canonical_zh") or "").strip()
            if canonical_en:
                override["en"] = canonical_en
            if canonical_zh:
                override["zh"] = canonical_zh
            if override:
                canonical_overrides[concept_id] = override
    return excluded, canonical_overrides, redirect_targets


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


def _override_canonical(metadata: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    canonical_en = str(override.get("canonical_en") or override.get("en") or "").strip()
    canonical_zh = str(override.get("canonical_zh") or override.get("zh") or "").strip()
    if not canonical_en and not canonical_zh:
        return metadata

    updated = dict(metadata)
    canonical = dict(updated.get("canonical") or {})
    if canonical_en:
        canonical["en"] = canonical_en
    if canonical_zh:
        canonical["zh"] = canonical_zh
    updated["canonical"] = canonical
    return updated


def _candidate_record(
    *,
    concept_id: str,
    item: dict[str, Any],
    row: dict[str, Any],
    compact_concepts: dict[str, Any],
    canonical_overrides: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    metadata = _override_canonical(
        _concept_metadata(concept_id, item, compact_concepts),
        (canonical_overrides or {}).get(concept_id) or {},
    )
    lang = str(row.get("lang") or "zh")
    alias = str(row.get("alias") or "")
    return {
        "concept_id": concept_id,
        "canonical": metadata["canonical"],
        "domains": metadata["domains"],
        "parents": metadata["parents"],
        "specificity": metadata["specificity"],
        "candidate_type": _candidate_type(item),
        "candidate_source": "audit_blocked_row",
        "risk_tags": _risk_tags(item, row),
        "evidence_aliases": [{"lang": lang, "alias": alias}],
        "source_concept_id": concept_id,
        "target_hint": item.get("english_alias_target") or item.get("base_concept_target"),
        "reason": str(row.get("reason") or "blocked candidate requires paper context"),
    }


def _seed_alias_key(seed: dict[str, Any]) -> str:
    alias = str(seed.get("alias") or "").strip()
    if not alias:
        return ""
    lang = str(seed.get("lang") or "").strip().lower()
    alias_key = _concept_alias_key(alias)
    if lang in {"en", "zh"}:
        return f"{lang}:{alias_key.split(':', 1)[1]}"
    return alias_key


def _context_seed_records(
    *,
    context_seeds_path: Path | None,
    compact_concepts: dict[str, Any],
    deterministic_aliases: set[str],
    excluded_concepts: set[str],
    canonical_overrides: dict[str, dict[str, str]],
    curated_redirect_targets: set[str],
) -> list[tuple[str, dict[str, Any]]]:
    if not context_seeds_path or not Path(context_seeds_path).exists():
        return []
    payload = _read_json(Path(context_seeds_path))
    if str(payload.get("schema_version") or "") not in {"", CONTEXT_SEED_SCHEMA_VERSION}:
        raise ValueError(f"unsupported context seed schema: {payload.get('schema_version')}")

    records: list[tuple[str, dict[str, Any]]] = []
    for seed in payload.get("seeds") or []:
        if not isinstance(seed, dict):
            continue
        alias = str(seed.get("alias") or "").strip()
        alias_key = _seed_alias_key(seed)
        allow_deterministic_shadow = bool(seed.get("allow_deterministic_shadow", True))
        if not alias or not alias_key:
            continue
        if alias_key in deterministic_aliases and not allow_deterministic_shadow:
            continue
        lang = alias_key.split(":", 1)[0] if ":" in alias_key else ""
        if not _alias_allowed(lang, alias):
            continue
        target_concept_id = str(seed.get("target_concept_id") or seed.get("concept_id") or "").strip()
        if not target_concept_id:
            continue
        if target_concept_id not in compact_concepts and target_concept_id not in curated_redirect_targets:
            continue
        source_concept_id = str(seed.get("source_concept_id") or target_concept_id)
        if target_concept_id in excluded_concepts or source_concept_id in excluded_concepts:
            continue
        metadata = _override_canonical(
            _override_canonical(
                _concept_metadata(target_concept_id, seed, compact_concepts),
                seed,
            ),
            canonical_overrides.get(target_concept_id) or {},
        )
        risk_tags = {str(value) for value in seed.get("risk_tags") or [] if value}
        risk_tags.update({"explicit_context_seed", "needs_context"})
        record = {
            "concept_id": target_concept_id,
            "canonical": metadata["canonical"],
            "domains": metadata["domains"],
            "parents": metadata["parents"],
            "specificity": metadata["specificity"],
            "candidate_type": str(seed.get("candidate_type") or "explicit_context_alternative"),
            "candidate_source": "explicit_context_seed",
            "risk_tags": sorted(risk_tags),
            "evidence_aliases": [{"lang": lang, "alias": alias}],
            "source_concept_id": source_concept_id,
            "target_hint": seed.get("target_hint"),
            "reason": str(seed.get("reason") or "explicit context seed requires host-agent evidence"),
            "requires_context": bool(seed.get("requires_context", True)),
            "allow_deterministic_shadow": allow_deterministic_shadow,
        }
        resolution_group = str(seed.get("resolution_group") or "").strip()
        if resolution_group:
            record["resolution_group"] = resolution_group
        records.append((alias_key, record))
    return records


def build_ambiguous_alias_candidates(
    *,
    audit_path: Path,
    review_decisions_path: Path | None,
    alias_index_path: Path,
    curation_decisions_path: Path | None = None,
    context_seeds_path: Path | None = None,
    output_path: Path,
    manifest_path: Path | None = None,
    tool_output_path: Path | None = None,
    tool_manifest_path: Path | None = None,
) -> dict[str, Any]:
    audit_items = _audit_item_map(Path(audit_path))
    review_rows = _read_jsonl(review_decisions_path)
    rejected = _review_rejects(review_rows)
    excluded, canonical_overrides, curated_redirect_targets = _active_curation_metadata(curation_decisions_path)
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
        if concept_id not in compact_concepts and concept_id not in curated_redirect_targets:
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
                    canonical_overrides=canonical_overrides,
                )
            )

    for alias_key, record in _context_seed_records(
        context_seeds_path=context_seeds_path,
        compact_concepts=compact_concepts,
        deterministic_aliases=deterministic_aliases,
        excluded_concepts=excluded,
        canonical_overrides=canonical_overrides,
        curated_redirect_targets=curated_redirect_targets,
    ):
        candidates[alias_key].append(record)

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
    source_counts = Counter(
        str(candidate.get("candidate_source") or "audit_blocked_row")
        for records in normalized_candidates.values()
        for candidate in records
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
        "candidate_source_counts": dict(sorted(source_counts.items())),
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
    parser.add_argument("--context-seeds", type=Path)
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
        context_seeds_path=args.context_seeds,
        output_path=args.output,
        manifest_path=args.manifest,
        tool_output_path=args.tool_output,
        tool_manifest_path=args.tool_manifest,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
