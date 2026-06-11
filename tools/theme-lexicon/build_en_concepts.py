"""Build deterministic English concept snapshots from normalized source terms."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Iterable

SOURCE_ORDER = (
    ("openalex_topics", "00_openalex_en_concepts.jsonl"),
    ("ieee_taxonomy", "01_ieee_en_concepts.jsonl"),
    ("cso", "02_cso_en_concepts.jsonl"),
    ("physh", "03_physh_en_concepts.jsonl"),
    ("mesh", "04_mesh_en_concepts.jsonl"),
    ("arxiv", "05_arxiv_en_concepts.jsonl"),
)

NORMALIZED_FILENAMES = {
    "arxiv": "arxiv_terms.jsonl",
    "openalex_topics": "openalex_topics_terms.jsonl",
    "ieee_taxonomy": "ieee_taxonomy_terms.jsonl",
    "physh": "physh_terms.jsonl",
    "cso": "cso_terms.jsonl",
    "mesh": "mesh_terms.jsonl",
}

GENERIC_DOMAIN_FAMILIES = {
    "physical_sciences": "physical_sciences",
    "physics": "physical_sciences",
    "physics_and_astronomy": "physical_sciences",
    "engineering": "engineering",
    "electrical_engineering": "engineering",
    "communications": "engineering",
    "communications_technology": "engineering",
    "computer_science": "computer_science",
    "biomedical": "biomedical",
    "medicine": "biomedical",
    "life_sciences": "biomedical",
    "chemicals_and_drugs": "biomedical",
    "diseases": "biomedical",
    "mathematics": "mathematics",
    "statistics": "mathematics",
    "social_sciences": "social_sciences",
    "economics": "social_sciences",
}

COMPATIBLE_FAMILIES = {
    "physical_sciences": {"physical_sciences", "engineering", "mathematics", "computer_science"},
    "engineering": {"engineering", "physical_sciences", "computer_science", "mathematics"},
    "computer_science": {"computer_science", "engineering", "mathematics", "physical_sciences"},
    "mathematics": {"mathematics", "computer_science", "engineering", "physical_sciences"},
    "biomedical": {"biomedical"},
    "social_sciences": {"social_sciences", "mathematics"},
}


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _title_label(value: str) -> str:
    value = _clean_text(value)
    if not value:
        return value
    if value.isupper() and len(value) <= 8:
        return value
    return " ".join(word if word.isupper() and len(word) <= 4 else word.capitalize() for word in value.split())


def _slug(value: str) -> str:
    value = normalize_alias_key(value)
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "unknown"


def _singular_token(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("es") and not token.endswith(("ses", "xes")):
        return token[:-2]
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def normalize_alias_key(value: str) -> str:
    value = _clean_text(value).casefold()
    value = value.replace("&", " and ")
    value = re.sub(r"[\-_/]+", " ", value)
    value = re.sub(r"[^a-z0-9\s]+", " ", value)
    tokens = [_singular_token(token) for token in value.split() if token]
    return " ".join(tokens)


def _looks_like_external_identifier(value: str) -> bool:
    text = _clean_text(value)
    if not text:
        return False
    folded = text.casefold()
    if re.fullmatch(r"\d+", text):
        return True
    if re.fullmatch(r"m\.[0-9][0-9a-z]*(?:[ _-][0-9a-z]+)*", folded):
        return True
    if re.search(r"https?://", text, re.IGNORECASE):
        return True
    if re.search(r"@[a-z]{2}(?:-[A-Z]{2})?\s*\.?$", text):
        return True
    return False


def _source_ref(record: dict[str, Any]) -> dict[str, str]:
    ref = {"source": str(record.get("source") or ""), "label": str(record.get("label") or "")}
    if record.get("source_id"):
        ref["source_id"] = str(record["source_id"])
    return ref


def _unique(values: Iterable[str]) -> list[str]:
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


def _domain_families(domains: Iterable[str]) -> set[str]:
    families: set[str] = set()
    for domain in domains:
        clean = re.sub(r"[^a-z0-9]+", "_", str(domain or "").casefold()).strip("_")
        if not clean:
            continue
        families.add(GENERIC_DOMAIN_FAMILIES.get(clean, clean))
    return families


def _domains_compatible(existing: Iterable[str], incoming: Iterable[str]) -> bool:
    left = _domain_families(existing)
    right = _domain_families(incoming)
    if not left or not right:
        return True
    if left & right:
        return True
    for family in left:
        if COMPATIBLE_FAMILIES.get(family, {family}) & right:
            return True
    return False


def _specificity(label: str, aliases: Iterable[str], domains: Iterable[str]) -> int:
    key = normalize_alias_key(label)
    token_count = len(key.split())
    score = min(100, token_count * 18 + min(len(key), 60))
    if any(domain in {"biomedical", "engineering", "computer_science"} for domain in _domain_families(domains)):
        score += 5
    if any(len(normalize_alias_key(alias).split()) >= 3 for alias in aliases):
        score += 5
    return min(score, 100)


def _empty_concept(concept_id: str, canonical_en: str) -> dict[str, Any]:
    return {
        "concept_id": concept_id,
        "canonical": {"en": canonical_en, "zh": None},
        "aliases": {"en": [], "zh": []},
        "source_refs": [],
        "domains": [],
        "parents": [],
        "specificity": 0,
        "status": "english_only",
        "review_status": "auto_merged",
    }


def _concept_sort_key(concept: dict[str, Any]) -> tuple[str, str]:
    return (str(concept.get("concept_id") or ""), str((concept.get("canonical") or {}).get("en") or ""))


def _jsonl_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    ordered = sorted(records, key=_concept_sort_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in ordered:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return len(ordered)


def _make_unique_concept_id(base: str, concepts: dict[str, dict[str, Any]]) -> str:
    concept_id = f"concept:{base}"
    if concept_id not in concepts:
        return concept_id
    index = 2
    while f"concept:{base}__{index}" in concepts:
        index += 1
    return f"concept:{base}__{index}"


def _find_merge_target(
    keys: set[str],
    domains: list[str],
    key_to_concepts: dict[str, set[str]],
    concepts: dict[str, dict[str, Any]],
) -> str | None:
    candidates: list[str] = []
    for key in sorted(keys):
        candidates.extend(sorted(key_to_concepts.get(key, set())))
    seen: set[str] = set()
    for concept_id in candidates:
        if concept_id in seen:
            continue
        seen.add(concept_id)
        concept = concepts.get(concept_id)
        if concept and _domains_compatible(concept.get("domains") or [], domains):
            return concept_id
    return None


def _merge_record(
    record: dict[str, Any],
    concepts: dict[str, dict[str, Any]],
    key_to_concepts: dict[str, set[str]],
) -> None:
    label = _clean_text(record.get("label"))
    if _looks_like_external_identifier(label):
        return
    aliases = _unique(
        alias
        for alias in [label, *(record.get("aliases") or [])]
        if not _looks_like_external_identifier(str(alias))
    )
    if not aliases:
        return
    keys = {normalize_alias_key(alias) for alias in aliases if normalize_alias_key(alias)}
    domains = [str(domain) for domain in (record.get("domains") or []) if str(domain or "")]
    target_id = _find_merge_target(keys, domains, key_to_concepts, concepts)
    if target_id is None:
        target_id = _make_unique_concept_id(_slug(label), concepts)
        concepts[target_id] = _empty_concept(target_id, _title_label(label))
    concept = concepts[target_id]
    concept["aliases"]["en"] = _unique([*(concept["aliases"].get("en") or []), *aliases])
    concept["domains"] = sorted(set([*(concept.get("domains") or []), *domains]))
    concept["source_refs"] = _dedupe_refs([*(concept.get("source_refs") or []), _source_ref(record)])
    concept["specificity"] = _specificity(concept["canonical"]["en"], concept["aliases"]["en"], concept["domains"])
    for key in keys:
        key_to_concepts[key].add(target_id)


def _dedupe_refs(refs: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for ref in refs:
        clean = {k: str(v) for k, v in ref.items() if v is not None and str(v)}
        key = (clean.get("source", ""), clean.get("source_id", ""), clean.get("label", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(clean)
    return out


def build_en_concepts(
    *,
    normalized_dir: Path,
    output_dir: Path,
    sources: Iterable[tuple[str, str]] = SOURCE_ORDER,
) -> dict[str, Any]:
    normalized_dir = Path(normalized_dir)
    output_dir = Path(output_dir)
    concepts: dict[str, dict[str, Any]] = {}
    key_to_concepts: dict[str, set[str]] = defaultdict(set)
    summary: dict[str, Any] = {
        "schema_version": "theme_en_concept_build.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "normalized_dir": str(normalized_dir.resolve()),
        "output_dir": str(output_dir.resolve()),
        "snapshots": [],
    }
    for source, snapshot_name in sources:
        source_path = normalized_dir / NORMALIZED_FILENAMES[source]
        records = _jsonl_records(source_path)
        for record in sorted(records, key=lambda rec: (str(rec.get("source_id") or ""), str(rec.get("label") or ""))):
            _merge_record(record, concepts, key_to_concepts)
        snapshot_path = output_dir / snapshot_name
        count = _write_jsonl(snapshot_path, concepts.values())
        summary["snapshots"].append({"source": source, "input_records": len(records), "output": str(snapshot_path), "concepts": count})
    merged_path = output_dir / "merged_en_concept_candidates.jsonl"
    summary["total_concepts"] = _write_jsonl(merged_path, concepts.values())
    summary["merged_output"] = str(merged_path)
    manifest_path = output_dir / "en_concept_build_manifest.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    summary["manifest"] = str(manifest_path)
    manifest_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized-dir", type=Path, default=Path("lexicons/normalized"))
    parser.add_argument("--output-dir", type=Path, default=Path("lexicons/builds"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = build_en_concepts(normalized_dir=args.normalized_dir, output_dir=args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
