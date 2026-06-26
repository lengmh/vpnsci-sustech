"""Validate theme concept alias candidates and write review artifacts."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Iterable

BUILTIN_GENERIC_ZH = {"系统", "模型", "方法", "研究", "网络", "目的", "通过", "进行", "治疗"}
BUILTIN_GENERIC_EN = {"system", "systems", "model", "models", "method", "methods", "research", "study", "studies", "analysis"}


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_alias(value: str) -> str:
    text = _clean_text(value).casefold()
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        text = re.sub(r"(?<=[\u4e00-\u9fff])(?=[A-Za-z0-9])", " ", text)
        text = re.sub(r"(?<=[A-Za-z0-9])(?=[\u4e00-\u9fff])", " ", text)
    text = text.replace("∞", " infinity ")
    text = text.replace("&", " and ")
    text = re.sub(r"[\-_/]+", " ", text)
    text = re.sub(r"[^\w\s\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _is_zh(value: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in value)


def _is_acronym(value: str) -> bool:
    alias = _clean_text(value)
    if _is_zh(alias):
        return False
    return 2 <= len(alias) <= 5 and alias.upper() == alias and alias.replace("-", "").isalpha()


def _non_acronym_ascii_segment_count(value: str) -> int:
    count = 0
    for segment in re.findall(r"[A-Za-z][A-Za-z0-9]*", _clean_text(value)):
        if segment.isupper() and len(segment) <= 8:
            continue
        if re.fullmatch(r"[A-Za-z]?\d+[A-Za-z]*|[A-Za-z]+[0-9]+", segment):
            continue
        count += 1
    return count


def _is_low_confidence_mixed_fallback(item: dict[str, Any]) -> bool:
    candidate = item.get("candidate")
    if not isinstance(candidate, dict):
        return False
    if candidate.get("source") != "agent_review_gated_mixed_fallback":
        return False
    if candidate.get("confidence") != "low":
        return False
    return _non_acronym_ascii_segment_count(str(item.get("alias") or "")) > 0


def _is_english_heavy_zh_candidate(item: dict[str, Any]) -> bool:
    candidate = item.get("candidate")
    if not isinstance(candidate, dict):
        return False
    source = str(candidate.get("source") or "")
    if source not in {"agent_compositional_glossary", "agent_mixed_class_suffix", "agent_review_gated_mixed_fallback"}:
        return False
    return _non_acronym_ascii_segment_count(str(item.get("alias") or "")) >= 3


def _has_ordinary_english_residue(item: dict[str, Any]) -> bool:
    candidate = item.get("candidate")
    if not isinstance(candidate, dict):
        return False
    source = str(candidate.get("source") or "")
    if not source.startswith("agent_") or source == "agent_exact_glossary":
        return False
    return _non_acronym_ascii_segment_count(str(item.get("alias") or "")) > 0


def _shape_rejection_reason(alias: str) -> str:
    text = _clean_text(alias)
    folded = text.casefold()
    if re.fullmatch(r"\d+", text):
        return "external numeric identifier is source metadata only"
    if re.fullmatch(r"m\.[0-9][0-9a-z]*(?:[ _-][0-9a-z]+)*", folded):
        return "external machine identifier is source metadata only"
    if re.search(r"https?://", text, re.IGNORECASE):
        return "external URL is source metadata only"
    if re.search(r"@[a-z]{2}(?:-[A-Z]{2})?\s*\.?$", text):
        return "RDF language-tagged literal must be cleaned before runtime aliasing"
    if len(text) > 80:
        return "alias is too long for runtime matching"
    if not _is_zh(text) and re.match(r"^[A-Za-z][A-Za-z0-9'() .-]+,\s*[A-Za-z]", text):
        return "inverted English/source alias is source evidence only"
    return ""


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


def _load_theme_generics(repo_root: Path) -> tuple[set[str], set[str]]:
    zh = set(BUILTIN_GENERIC_ZH)
    en = set(BUILTIN_GENERIC_EN)
    zh_path = repo_root / "vpnsci_sustech" / "data" / "theme_lexicon.zh.json"
    en_path = repo_root / "vpnsci_sustech" / "data" / "theme_lexicon.en.json"
    if zh_path.exists():
        payload = json.loads(zh_path.read_text(encoding="utf-8"))
        for key in ("generic_terms", "connector_terms"):
            zh.update(str(item) for item in payload.get(key) or [])
    if en_path.exists():
        payload = json.loads(en_path.read_text(encoding="utf-8"))
        for key in ("token_stopwords", "generic_label_terms"):
            en.update(str(item).casefold() for item in payload.get(key) or [])
    return zh, en


def _decision(
    *,
    concept_id: str,
    alias: str,
    lang: str,
    decision: str,
    review_tier: str,
    reason: str,
    reviewer: str,
    domains: list[str] | None = None,
    subagent_recommendation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "concept_id": concept_id,
        "alias": alias,
        "lang": lang,
        "decision": decision,
        "review_tier": review_tier,
        "reviewer": reviewer,
        "reason": reason,
        "domains": domains or [],
        "decided_at": datetime.now(timezone.utc).date().isoformat(),
    }
    if subagent_recommendation:
        row["subagent_recommendation"] = subagent_recommendation
    return row


def _candidate_files(candidate_dir: Path) -> list[Path]:
    manifest_path = Path(candidate_dir) / "zh_alias_candidate_manifest.json"
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        files: list[Path] = []
        for item in payload.get("batches") or []:
            if not isinstance(item, dict) or not item.get("output"):
                continue
            raw = Path(str(item["output"]))
            if raw.is_absolute():
                files.append(raw)
            elif raw.exists():
                files.append(raw)
            else:
                files.append(Path(candidate_dir) / raw.name)
        return sorted(files)
    return sorted(Path(candidate_dir).glob("zh_alias_candidates.batch-*.jsonl"))


def _iter_candidate_rows(candidate_dir: Path) -> Iterable[dict[str, Any]]:
    for path in _candidate_files(candidate_dir):
        yield from _read_jsonl(path)


def validate_alias_overlay(
    *,
    candidate_dir: Path,
    output_dir: Path,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    candidate_dir = Path(candidate_dir)
    output_dir = Path(output_dir)
    repo_root = Path(repo_root or Path.cwd())
    generic_zh, generic_en = _load_theme_generics(repo_root)

    alias_to_concepts: dict[str, set[str]] = defaultdict(set)
    alias_rows: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []

    for row in _iter_candidate_rows(candidate_dir):
        concept_id = str(row.get("concept_id") or "")
        domains = [str(domain) for domain in (row.get("domains") or []) if str(domain or "")]
        canonical_en = _clean_text(row.get("canonical_en"))
        english_aliases = [canonical_en, *[str(alias) for alias in (row.get("aliases_en") or [])]]
        for alias in english_aliases:
            alias = _clean_text(alias)
            if not alias:
                continue
            norm = _normalize_alias(alias)
            alias_to_concepts[f"en:{norm}"].add(concept_id)
            alias_rows.append({"concept_id": concept_id, "alias": alias, "lang": "en", "domains": domains})
        for candidate in row.get("zh_alias_candidates") or []:
            if not isinstance(candidate, dict):
                continue
            alias = _clean_text(candidate.get("alias"))
            if not alias:
                continue
            norm = _normalize_alias(alias)
            alias_to_concepts[f"zh:{norm}"].add(concept_id)
            alias_rows.append({"concept_id": concept_id, "alias": alias, "lang": "zh", "domains": domains, "candidate": candidate})

    alias_conflicts: list[dict[str, Any]] = []
    ambiguous_abbreviations: list[dict[str, Any]] = []
    generic_rejections: list[dict[str, Any]] = []
    shape_rejections: list[dict[str, Any]] = []

    conflicted_keys = {key for key, concept_ids in alias_to_concepts.items() if len(concept_ids) > 1}
    for key in sorted(conflicted_keys):
        lang, norm = key.split(":", 1)
        alias_conflicts.append({"alias_key": norm, "lang": lang, "concept_ids": sorted(alias_to_concepts[key]), "reason": "alias maps to multiple concepts"})

    for item in alias_rows:
        concept_id = item["concept_id"]
        alias = item["alias"]
        lang = item["lang"]
        domains = item.get("domains") or []
        norm = _normalize_alias(alias)
        key = f"{lang}:{norm}"
        is_generic = alias in generic_zh if lang == "zh" else norm in generic_en
        shape_reason = _shape_rejection_reason(alias)
        if is_generic:
            generic_rejections.append({"concept_id": concept_id, "alias": alias, "lang": lang, "reason": "generic/noise alias"})
            decisions.append(_decision(
                concept_id=concept_id,
                alias=alias,
                lang=lang,
                decision="reject",
                review_tier="reject",
                reviewer="validator",
                reason="generic/noise alias cannot become active runtime alias",
                domains=domains,
            ))
        elif shape_reason:
            shape_rejections.append({"concept_id": concept_id, "alias": alias, "lang": lang, "reason": shape_reason})
            decisions.append(_decision(
                concept_id=concept_id,
                alias=alias,
                lang=lang,
                decision="reject",
                review_tier="reject",
                reviewer="validator",
                reason=shape_reason,
                domains=domains,
            ))
        elif key in conflicted_keys:
            decisions.append(_decision(
                concept_id=concept_id,
                alias=alias,
                lang=lang,
                decision="blocked",
                review_tier="review_blocked",
                reviewer="validator",
                reason="alias collision blocked until duplicate concept merge or explicit runtime target is resolved",
                domains=domains,
            ))
        elif lang == "zh" and _is_low_confidence_mixed_fallback(item):
            decisions.append(_decision(
                concept_id=concept_id,
                alias=alias,
                lang=lang,
                decision="blocked",
                review_tier="review_blocked",
                reviewer="validator",
                reason="low-confidence mixed fallback leaves untranslated English residue; block pending domain-specific translation",
                domains=domains,
            ))
        elif lang == "zh" and _is_english_heavy_zh_candidate(item):
            decisions.append(_decision(
                concept_id=concept_id,
                alias=alias,
                lang=lang,
                decision="blocked",
                review_tier="review_blocked",
                reviewer="validator",
                reason="Chinese candidate leaves three or more ordinary English words; block pending domain-specific translation",
                domains=domains,
            ))
        elif lang == "zh" and _has_ordinary_english_residue(item):
            decisions.append(_decision(
                concept_id=concept_id,
                alias=alias,
                lang=lang,
                decision="blocked",
                review_tier="review_blocked",
                reviewer="validator",
                reason="Chinese candidate leaves ordinary untranslated English residue; block pending exact or domain-specific translation",
                domains=domains,
            ))
        elif _is_acronym(alias):
            ambiguous_abbreviations.append({"concept_id": concept_id, "alias": alias, "lang": lang, "domains": domains, "reason": "short acronym needs review"})
            decisions.append(_decision(
                concept_id=concept_id,
                alias=alias,
                lang=lang,
                decision="needs_review",
                review_tier="needs_review",
                reviewer="validator",
                reason="short acronym requires review",
                domains=domains,
            ))
        elif lang == "zh":
            decisions.append(_decision(
                concept_id=concept_id,
                alias=alias,
                lang=lang,
                decision="needs_review",
                review_tier="needs_review",
                reviewer="validator",
                reason="Chinese alias candidate requires SubAgent recommendation and main-Agent acceptance",
                domains=domains,
            ))
        else:
            decisions.append(_decision(
                concept_id=concept_id,
                alias=alias,
                lang=lang,
                decision="accept",
                review_tier="auto_accept",
                reviewer="validator",
                reason="English alias passed deterministic validators",
                domains=domains,
            ))

    duplicate_concepts: list[dict[str, Any]] = []
    parent_child_collisions: list[dict[str, Any]] = []

    counts = {
        "schema_version": "theme_alias_validation.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_dir": str(candidate_dir.resolve()),
        "output_dir": str(output_dir.resolve()),
        "alias_conflicts": _write_jsonl(output_dir / "alias_conflicts.jsonl", alias_conflicts),
        "ambiguous_abbreviations": _write_jsonl(output_dir / "ambiguous_abbreviations.jsonl", ambiguous_abbreviations),
        "duplicate_concepts": _write_jsonl(output_dir / "duplicate_concepts.jsonl", duplicate_concepts),
        "parent_child_collisions": _write_jsonl(output_dir / "parent_child_collisions.jsonl", parent_child_collisions),
        "generic_rejections": _write_jsonl(output_dir / "generic_rejections.jsonl", generic_rejections),
        "alias_shape_rejections": _write_jsonl(output_dir / "alias_shape_rejections.jsonl", shape_rejections),
        "review_decisions": _write_jsonl(output_dir / "review_decisions.jsonl", decisions),
    }
    manifest_path = output_dir / "alias_validation_manifest.json"
    counts["manifest"] = str(manifest_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(counts, ensure_ascii=False, indent=2), encoding="utf-8")
    return counts


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, default=Path("lexicons/candidates"))
    parser.add_argument("--output-dir", type=Path, default=Path("lexicons/review"))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = validate_alias_overlay(candidate_dir=args.candidate_dir, output_dir=args.output_dir, repo_root=args.repo_root)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
