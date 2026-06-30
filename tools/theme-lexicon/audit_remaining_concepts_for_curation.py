"""Audit remaining uncovered theme concepts for concept-curation review.

This is a read-only C1 helper for the theme concept alias pipeline.  It reads
the compact runtime index plus review decisions, then writes curation review
inputs under the temp directory.  It does not mutate runtime data.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import re
from typing import Any

from query_alias_index import normalize_alias


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INDEX_PATH = REPO_ROOT / "vpnsci_sustech" / "data" / "theme_concept_alias_index.json"
DEFAULT_REVIEW_DECISIONS_PATH = REPO_ROOT / "lexicons" / "review" / "review_decisions.jsonl"
DEFAULT_OUTPUT_DIR = Path("F:/AI playground/TempFiles")

COLLISION_REASON_PREFIX = "alias collision blocked"

BROAD_OR_NOISE_CANONICALS = {
    "abstract",
    "abstracts",
    "application",
    "applications",
    "assessment",
    "assessments",
    "beauty",
    "co",
    "error",
    "errors",
    "model",
    "models",
    "performance",
    "platform",
    "platforms",
    "review",
    "reviews",
    "solution",
    "solutions",
    "system",
    "systems",
}

SOURCE_ARTIFACT_CANONICALS = {
    "abas",
    "acme",
    "acmestudio",
    "alma",
    "alpsm",
    "applied co",
}

TOPIC_LABEL_PATTERNS = [
    re.compile(r"\badvanced\b.*\b(applications?|techniques?|research|studies|processes?|algorithms?)\b", re.I),
    re.compile(r"\b.+\s+and\s+(applications?|studies|research|learning|education|policy|policies|outcomes)\b", re.I),
    re.compile(r"\b.+\s+techniques?\s+and\s+applications?\b", re.I),
    re.compile(r"\b.+\s+technology\s+in\s+.+\b", re.I),
    re.compile(r"\b.+\s+research\s+and\s+education\s+studies\b", re.I),
]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _canonical_en(concept: dict[str, Any]) -> str:
    return _clean((concept.get("canonical") or {}).get("en"))


def _canonical_zh(concept: dict[str, Any]) -> str:
    return _clean((concept.get("canonical") or {}).get("zh"))


def _base_concept_id(concept_id: str) -> str:
    return re.sub(r"__\d+$", "", concept_id)


def _has_variant_suffix(concept_id: str) -> bool:
    return bool(re.search(r"__\d+$", concept_id))


def _is_probable_plural_variant(en: str) -> bool:
    normalized = normalize_alias(en)
    raw = en.casefold().strip()
    return raw.endswith("s") and not raw.endswith("ss") and normalized != raw


def _is_short_acronym_or_acronym_form(en: str) -> bool:
    text = _clean(en)
    if re.search(r"\([A-Za-z][A-Za-z0-9 .+-]{2,}\)", text):
        return True
    compact = re.sub(r"[^A-Za-z0-9]", "", text)
    if 2 <= len(compact) <= 6 and compact.upper() == compact and any(ch.isalpha() for ch in compact):
        return True
    # Many source labels are title-cased acronyms, e.g. "Agc" or "Atpg".
    if 2 <= len(compact) <= 5 and text.count(" ") == 0 and sum(ch.lower() in "aeiou" for ch in compact) <= 1:
        return True
    return False


def _is_topic_label_phrase(en: str) -> bool:
    text = _clean(en)
    return any(pattern.search(text) for pattern in TOPIC_LABEL_PATTERNS)


def _is_broad_or_noise(en: str) -> bool:
    key = normalize_alias(en)
    if key in BROAD_OR_NOISE_CANONICALS or key in SOURCE_ARTIFACT_CANONICALS:
        return True
    # One-token titlecase labels in computer/source dumps are often artifacts.
    compact = re.sub(r"[^A-Za-z0-9]", "", en)
    return 3 <= len(compact) <= 12 and " " not in en and key in SOURCE_ARTIFACT_CANONICALS


def _topic_label_suggestion(en: str, has_target: bool) -> str:
    key = normalize_alias(en)
    if has_target:
        return "suggested_redirect"
    if "advanced" in key and any(token in key for token in ("applications", "techniques", "research", "studies")):
        return "suggested_suppressed"
    if " technology in " in f" {key} " or key.endswith(" and learning"):
        return "suggested_display_only"
    return "suggested_canonical_review"


def _target_summary(concept_id: str | None, concepts: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if not concept_id or concept_id not in concepts:
        return None
    concept = concepts[concept_id]
    return {
        "concept_id": concept_id,
        "canonical_en": _canonical_en(concept),
        "canonical_zh": _canonical_zh(concept),
        "domains": concept.get("domains") or [],
    }


def _load_zh_review_rows(path: Path, uncovered_ids: set[str]) -> dict[str, list[dict[str, Any]]]:
    rows_by_concept: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            concept_id = str(row.get("concept_id") or "")
            if concept_id not in uncovered_ids or row.get("lang") != "zh":
                continue
            rows_by_concept[concept_id].append(
                {
                    "alias": _clean(row.get("alias")),
                    "decision": row.get("decision"),
                    "reason": _clean(row.get("reason")),
                    "review_tier": row.get("review_tier"),
                    "reviewer": row.get("reviewer"),
                }
            )
    return rows_by_concept


def _collision_alias_targets(
    *,
    rows: list[dict[str, Any]],
    aliases: dict[str, str],
    concepts: dict[str, dict[str, Any]],
    concept_id: str,
) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        reason = str(row.get("reason") or "")
        if not reason.startswith(COLLISION_REASON_PREFIX):
            continue
        alias = _clean(row.get("alias"))
        alias_key = f"zh:{normalize_alias(alias)}"
        target_id = aliases.get(alias_key)
        if not target_id or target_id == concept_id:
            continue
        key = (alias, target_id)
        if key in seen:
            continue
        seen.add(key)
        target = _target_summary(target_id, concepts)
        targets.append(
            {
                "alias": alias,
                "alias_key": alias_key,
                "target": target,
            }
        )
    return targets


def _english_alias_target(
    *,
    en: str,
    aliases: dict[str, str],
    concepts: dict[str, dict[str, Any]],
    concept_id: str,
) -> dict[str, Any] | None:
    alias_key = f"en:{normalize_alias(en)}"
    target_id = aliases.get(alias_key)
    if not target_id or target_id == concept_id:
        return None
    return {"alias_key": alias_key, "target": _target_summary(target_id, concepts)}


def _base_id_target(concept_id: str, concepts: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    base_id = _base_concept_id(concept_id)
    if base_id == concept_id or base_id not in concepts:
        return None
    return _target_summary(base_id, concepts)


def _classify_item(
    *,
    concept_id: str,
    concept: dict[str, Any],
    rows: list[dict[str, Any]],
    aliases: dict[str, str],
    concepts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    en = _canonical_en(concept)
    domains = concept.get("domains") or []
    collision_targets = _collision_alias_targets(rows=rows, aliases=aliases, concepts=concepts, concept_id=concept_id)
    english_target = _english_alias_target(en=en, aliases=aliases, concepts=concepts, concept_id=concept_id)
    base_target = _base_id_target(concept_id, concepts)
    has_target = bool(collision_targets or english_target or base_target)

    categories: list[str] = []
    if collision_targets:
        categories.append("collision_redirect_candidate")
    if _has_variant_suffix(concept_id) or _is_probable_plural_variant(en) or english_target or base_target:
        categories.append("plural_or_source_variant")
    if _is_short_acronym_or_acronym_form(en):
        categories.append("acronym_full_form_duplicate" if has_target else "acronym_or_short_label")
    if _is_broad_or_noise(en):
        categories.append("broad_or_noise")
    if _is_topic_label_phrase(en):
        categories.append("topic_label_phrase")

    if not categories:
        categories.append("true_singleton_gap")

    if "collision_redirect_candidate" in categories or (
        has_target and ("plural_or_source_variant" in categories or "acronym_full_form_duplicate" in categories)
    ):
        primary_bucket = "redirect_candidates"
    elif "broad_or_noise" in categories:
        primary_bucket = "suppressed_candidates"
    elif "topic_label_phrase" in categories:
        primary_bucket = "topic_label_candidates"
    elif any(category in categories for category in ("plural_or_source_variant", "acronym_or_short_label", "acronym_full_form_duplicate")):
        primary_bucket = "needs_decision_candidates"
    else:
        primary_bucket = "singleton_gaps"

    topic_label_suggestion = None
    if "topic_label_phrase" in categories:
        topic_label_suggestion = _topic_label_suggestion(en, has_target)

    decisions = Counter(str(row.get("decision") or "") for row in rows)
    collision_row_count = sum(1 for row in rows if str(row.get("reason") or "").startswith(COLLISION_REASON_PREFIX))

    return {
        "concept_id": concept_id,
        "canonical_en": en,
        "domains": domains,
        "categories": categories,
        "primary_bucket": primary_bucket,
        "topic_label_suggestion": topic_label_suggestion,
        "review_decision_counts": dict(sorted(decisions.items())),
        "zh_review_row_count": len(rows),
        "zh_collision_row_count": collision_row_count,
        "collision_alias_targets": collision_targets,
        "english_alias_target": english_target,
        "base_concept_target": base_target,
        "sample_zh_review_rows": rows[:5],
    }


def audit_remaining_concepts_for_curation(
    *,
    index_path: Path,
    review_decisions_path: Path,
    output_dir: Path,
    stamp: str,
) -> dict[str, Any]:
    payload = _read_json(index_path)
    concepts: dict[str, dict[str, Any]] = payload.get("concepts") or {}
    aliases: dict[str, str] = payload.get("aliases") or {}
    uncovered = {
        concept_id: concept
        for concept_id, concept in concepts.items()
        if not _canonical_zh(concept)
    }
    rows_by_concept = _load_zh_review_rows(review_decisions_path, set(uncovered))

    items = [
        _classify_item(
            concept_id=concept_id,
            concept=concept,
            rows=rows_by_concept.get(concept_id, []),
            aliases=aliases,
            concepts=concepts,
        )
        for concept_id, concept in sorted(uncovered.items())
    ]

    category_counts = Counter(category for item in items for category in item["categories"])
    bucket_counts = Counter(item["primary_bucket"] for item in items)
    decision_counts = Counter()
    collision_blocked_concepts = 0
    no_zh_review_row_count = 0
    for item in items:
        decision_counts.update(item["review_decision_counts"])
        if item["zh_collision_row_count"]:
            collision_blocked_concepts += 1
        if not item["zh_review_row_count"]:
            no_zh_review_row_count += 1

    redirect_candidates = [item for item in items if item["primary_bucket"] == "redirect_candidates"]
    suppressed_candidates = [item for item in items if item["primary_bucket"] == "suppressed_candidates"]
    singleton_gaps = [item for item in items if item["primary_bucket"] == "singleton_gaps"]
    topic_label_candidates = [item for item in items if item["primary_bucket"] == "topic_label_candidates"]
    needs_decision_candidates = [item for item in items if item["primary_bucket"] == "needs_decision_candidates"]

    output_dir.mkdir(parents=True, exist_ok=True)
    audit_path = output_dir / f"theme_alias_remaining_concept_curation_audit_{stamp}.json"
    redirect_path = output_dir / f"theme_alias_remaining_concept_curation_redirect_candidates_{stamp}.json"
    suppressed_path = output_dir / f"theme_alias_remaining_concept_curation_suppressed_candidates_{stamp}.json"
    singleton_path = output_dir / f"theme_alias_remaining_concept_curation_singleton_gaps_{stamp}.json"
    topic_label_path = output_dir / f"theme_alias_remaining_concept_curation_topic_label_candidates_{stamp}.json"
    needs_decision_path = output_dir / f"theme_alias_remaining_concept_curation_needs_decision_candidates_{stamp}.json"

    summary = {
        "schema_version": "theme_remaining_concept_curation_audit.v1",
        "index_path": str(index_path.resolve()),
        "review_decisions_path": str(review_decisions_path.resolve()),
        "runtime_build_status": payload.get("build_status"),
        "raw_concepts": len(concepts),
        "raw_uncovered_concepts": len(uncovered),
        "raw_concepts_with_zh_alias": len(concepts) - len(uncovered),
        "raw_concepts_with_zh_alias_percent": round((len(concepts) - len(uncovered)) * 100 / len(concepts), 2),
        "zh_review_rows_for_uncovered": sum(item["zh_review_row_count"] for item in items),
        "collision_blocked_concepts": collision_blocked_concepts,
        "concepts_without_zh_review_rows": no_zh_review_row_count,
        "category_counts": dict(category_counts.most_common()),
        "primary_bucket_counts": dict(bucket_counts.most_common()),
        "zh_review_decision_counts_for_uncovered": dict(decision_counts.most_common()),
        "outputs": {
            "audit": str(audit_path),
            "redirect_candidates": str(redirect_path),
            "suppressed_candidates": str(suppressed_path),
            "singleton_gaps": str(singleton_path),
            "topic_label_candidates": str(topic_label_path),
            "needs_decision_candidates": str(needs_decision_path),
        },
        "samples": {
            "redirect_candidates": redirect_candidates[:25],
            "suppressed_candidates": suppressed_candidates[:25],
            "topic_label_candidates": topic_label_candidates[:25],
            "needs_decision_candidates": needs_decision_candidates[:25],
            "singleton_gaps": singleton_gaps[:25],
        },
    }

    _write_json(audit_path, {"summary": summary, "items": items})
    _write_json(redirect_path, {"summary": summary, "items": redirect_candidates})
    _write_json(suppressed_path, {"summary": summary, "items": suppressed_candidates})
    _write_json(singleton_path, {"summary": summary, "items": singleton_gaps})
    _write_json(topic_label_path, {"summary": summary, "items": topic_label_candidates})
    _write_json(needs_decision_path, {"summary": summary, "items": needs_decision_candidates})
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-path", type=Path, default=DEFAULT_INDEX_PATH)
    parser.add_argument("--review-decisions", type=Path, default=DEFAULT_REVIEW_DECISIONS_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--stamp", default=date.today().strftime("%Y%m%d"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = audit_remaining_concepts_for_curation(
        index_path=args.index_path,
        review_decisions_path=args.review_decisions,
        output_dir=args.output_dir,
        stamp=args.stamp,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
