"""Materialize reviewed concept aliases into tracked runtime overlay files.

This is the L5 offline promotion step. It reads ignored construction artifacts
under ``lexicons/`` and writes only accepted aliases to tracked compact runtime
index/manifest copies.

The script never reads raw source dumps, candidate rationale payloads, report
artifacts, or search artifacts.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable


DEFAULT_INDEX_OUTPUTS = (
    Path("vpnsci_sustech/data/theme_concept_alias_index.json"),
    Path("tools/paper-search-pro/assets/theme_concept_alias_index.json"),
)
DEFAULT_MANIFEST_OUTPUTS = (
    Path("vpnsci_sustech/data/theme_concept_alias_manifest.json"),
    Path("tools/paper-search-pro/assets/theme_concept_alias_manifest.json"),
)
DEFAULT_LEGACY_OUTPUTS: tuple[Path, ...] = ()
LEGACY_FULL_OUTPUTS = (
    Path("vpnsci_sustech/data/theme_concept_aliases.json"),
    Path("tools/paper-search-pro/assets/theme_concept_aliases.json"),
)
DEFAULT_OUTPUTS = LEGACY_FULL_OUTPUTS

KNOWN_BAD_ZH_ALIAS_SHAPES = {
    "BANGBANG",
    "Knapsack问题",
    "B7 1抗原",
    "B7 2抗原",
    "HCV NS3 4A蛋白酶抑制剂",
    "S相位",
    "休克波",
    "受体5-羟色胺",
    "心动过速心室",
    "心动过速窦",
    "智能智能体",
    "环路环路",
    "物联网物联网",
    "蛛网膜下腔出血创伤性",
    "识别识别",
    "费用泵",
    "质量疫苗接种",
    "钠水杨酸盐",
    "酸磷酸酶",
    "高能源休克波",
}


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _singular_alias_token(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith(("ches", "shes", "sses", "xes", "zes")):
        return token[:-2]
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _normalize_alias(value: str) -> str:
    text = _clean_text(value).casefold()
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return re.sub(r"[\s，。；;：:、（）()\[\]【】<>《》!?！？\-_／/]+", "", text)
    text = text.replace("&", " and ")
    text = re.sub(r"[\-_/]+", " ", text)
    text = re.sub(r"[^a-z0-9+\s]+", " ", text)
    return " ".join(_singular_alias_token(token) for token in text.split() if token)


def _normalize_review_alias(value: str) -> str:
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


def _json_bytes(payload: dict[str, Any], *, pretty: bool = False) -> bytes:
    if pretty:
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    else:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    return text.encode("utf-8")


def _write_json(path: Path, payload: dict[str, Any], *, pretty: bool = False) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _json_bytes(payload, pretty=pretty)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


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
        alias_to_concepts[(row["lang"], _normalize_review_alias(row["alias"]))].add(row["concept_id"])
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
        key = (row["lang"], _normalize_review_alias(row["alias"]))
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


def _build_runtime_index_payload(entries: list[dict[str, Any]], *, build_status: str) -> dict[str, Any]:
    concepts: dict[str, dict[str, Any]] = {}
    aliases: dict[str, str] = {}
    for entry in entries:
        concept_id = _clean_text(entry.get("concept_id"))
        if not concept_id:
            continue
        concepts[concept_id] = {
            "concept_id": concept_id,
            "canonical": entry.get("canonical") or {"en": "", "zh": ""},
            "domains": _unique_text(entry.get("domains") or []),
            "parents": _unique_text(entry.get("parents") or []),
            "specificity": int(entry.get("specificity") or 0),
        }
        for lang in ("en", "zh"):
            for alias in (entry.get("aliases") or {}).get(lang) or []:
                normalized = _normalize_alias(str(alias))
                if normalized:
                    aliases.setdefault(f"{lang}:{normalized}", concept_id)
    return {
        "schema_version": "theme_concept_alias_index.v1",
        "build_status": build_status,
        "normalization": "theme_concept_alias_normalization.v1",
        "concepts": dict(sorted(concepts.items())),
        "aliases": dict(sorted(aliases.items())),
    }


def _english_word_tokens(value: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z-]{2,}", value or "")


def _pollution_audit(entries: list[dict[str, Any]]) -> dict[str, int]:
    english_heavy = 0
    known_bad_hits = 0
    for entry in entries:
        for alias in (entry.get("aliases") or {}).get("zh") or []:
            text = str(alias)
            if any(bad in text for bad in KNOWN_BAD_ZH_ALIAS_SHAPES):
                known_bad_hits += 1
            if any("\u4e00" <= ch <= "\u9fff" for ch in text) and len(_english_word_tokens(text)) >= 3:
                english_heavy += 1
    return {
        "ordinary_english_heavy_zh_aliases": english_heavy,
        "known_bad_shape_hits": known_bad_hits,
    }


def _build_manifest_payload(
    *,
    entries: list[dict[str, Any]],
    review_summary: dict[str, int],
    skipped_conflicts: list[dict[str, Any]],
    index_sha256: str,
    build_status: str,
) -> dict[str, Any]:
    concept_count = len(entries)
    zh_count = sum(1 for entry in entries if (entry.get("aliases") or {}).get("zh"))
    en_aliases = sum(len((entry.get("aliases") or {}).get("en") or []) for entry in entries)
    zh_aliases = sum(len((entry.get("aliases") or {}).get("zh") or []) for entry in entries)
    return {
        "schema_version": "theme_concept_alias_manifest.v1",
        "build_status": build_status,
        "runtime_index_file": "theme_concept_alias_index.json",
        "concepts": concept_count,
        "concepts_with_zh_alias": zh_count,
        "concepts_with_zh_alias_percent": round((zh_count / concept_count * 100) if concept_count else 0.0, 2),
        "aliases": {"en": en_aliases, "zh": zh_aliases},
        "review_decision_row_summary": review_summary,
        "accepted_conflict_groups": len(skipped_conflicts),
        "runtime_alias_conflicts": {"en": 0, "zh": 0},
        "pollution_audit": _pollution_audit(entries),
        "sha256": {"index": index_sha256},
    }


def _build_legacy_full_payload(
    *,
    entries: list[dict[str, Any]],
    review_summary: dict[str, int],
    skipped_conflicts: list[dict[str, Any]],
    build_status: str,
) -> dict[str, Any]:
    return {
        "schema_version": "theme_concept_aliases.v1",
        "build_status": build_status,
        "review_decision_row_summary": review_summary,
        "skipped_accepted_alias_conflict_count": len(skipped_conflicts),
        "concept_aliases": entries,
    }


def materialize_runtime_overlay(
    *,
    concepts_path: Path,
    review_decisions_path: Path,
    index_outputs: Iterable[Path] | None = None,
    manifest_outputs: Iterable[Path] | None = None,
    legacy_outputs: Iterable[Path] | None = None,
    full_audit_output: Path | None = None,
    outputs: Iterable[Path] | None = None,
) -> dict[str, Any]:
    if outputs is not None:
        legacy_outputs = tuple(legacy_outputs or ()) + tuple(outputs)
        if index_outputs is None and manifest_outputs is None:
            index_outputs = ()
            manifest_outputs = ()
    if index_outputs is None:
        index_outputs = DEFAULT_INDEX_OUTPUTS
    if manifest_outputs is None:
        manifest_outputs = DEFAULT_MANIFEST_OUTPUTS
    if legacy_outputs is None:
        legacy_outputs = DEFAULT_LEGACY_OUTPUTS

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
    build_status = "partial_review_pending" if pending_review else "review_complete"

    index_payload = _build_runtime_index_payload(entries, build_status=build_status)
    index_written: list[str] = []
    index_sha256 = hashlib.sha256(_json_bytes(index_payload)).hexdigest()
    for output in index_outputs:
        output = Path(output)
        written_sha = _write_json(output, index_payload)
        index_sha256 = written_sha
        index_written.append(str(output))

    manifest_payload = _build_manifest_payload(
        entries=entries,
        review_summary=review_summary,
        skipped_conflicts=skipped_conflicts,
        index_sha256=index_sha256,
        build_status=build_status,
    )
    manifest_written: list[str] = []
    for output in manifest_outputs:
        output = Path(output)
        _write_json(output, manifest_payload, pretty=True)
        manifest_written.append(str(output))

    legacy_written: list[str] = []
    legacy_payload: dict[str, Any] | None = None
    if legacy_outputs:
        legacy_payload = _build_legacy_full_payload(
            entries=entries,
            review_summary=review_summary,
            skipped_conflicts=skipped_conflicts,
            build_status=build_status,
        )
        for output in legacy_outputs:
            output = Path(output)
            _write_json(output, legacy_payload, pretty=True)
            legacy_written.append(str(output))

    if full_audit_output:
        _write_jsonl(Path(full_audit_output), entries)

    return {
        "schema_version": "theme_concept_aliases_materialize.v2",
        "build_status": build_status,
        "concepts_loaded": len(concepts),
        "concept_aliases": len(entries),
        "missing_concepts": missing_concepts,
        "review_decision_row_summary": review_summary,
        "skipped_accepted_alias_conflicts": len(skipped_conflicts),
        "runtime_index_outputs": index_written,
        "manifest_outputs": manifest_written,
        "legacy_full_outputs": legacy_written,
        "full_audit_output": str(full_audit_output) if full_audit_output else None,
        "runtime_index_sha256": index_sha256,
        "outputs": legacy_written,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concepts", type=Path, default=Path("lexicons/builds/merged_en_concept_candidates.jsonl"))
    parser.add_argument("--review-decisions", type=Path, default=Path("lexicons/review/review_decisions.jsonl"))
    parser.add_argument("--index-output", action="append", type=Path, default=None)
    parser.add_argument("--manifest-output", action="append", type=Path, default=None)
    parser.add_argument("--legacy-output", action="append", type=Path, default=None)
    parser.add_argument(
        "--output",
        action="append",
        type=Path,
        default=None,
        help="Deprecated alias for --legacy-output.",
    )
    parser.add_argument("--full-audit-output", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = materialize_runtime_overlay(
        concepts_path=args.concepts,
        review_decisions_path=args.review_decisions,
        index_outputs=args.index_output or DEFAULT_INDEX_OUTPUTS,
        manifest_outputs=args.manifest_output or DEFAULT_MANIFEST_OUTPUTS,
        legacy_outputs=tuple(args.legacy_output or ()) + tuple(args.output or ()),
        full_audit_output=args.full_audit_output,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
