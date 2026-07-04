"""Host-agent resolution for ambiguous theme concept candidates.

Python owns the deterministic gates and result validation. The host Agent owns
the contextual judgment when a report has too little deterministic treemap
signal and an ambiguous alias candidate has direct paper/query evidence.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
import copy
from math import ceil
from typing import Any

from .theme_clustering import (
    LOW_SIGNAL_STATUS,
    RAW_LOW_SIGNAL_STATUS,
    _ambiguous_candidate_matches,
)


THEME_CANDIDATE_RESOLUTION_REQUEST_FILENAME = "theme_candidate_resolution_request.json"
THEME_CANDIDATE_RESOLUTION_RESULT_FILENAME = "theme_candidate_resolution_result.json"
REQUEST_SCHEMA_VERSION = "theme_candidate_resolution_request.v1"
RESULT_SCHEMA_VERSION = "theme_candidate_resolution_result.v1"

SYSTEM_PROMPT = """You are resolving ambiguous research-report theme candidates.

Rules:
1. Resolve only when title, abstract, keywords, or display_query provide direct evidence.
2. Do not choose broad semantic neighbors without contextual support.
3. Return unresolved when evidence is weak or absent.
4. Resolved candidates become formal theme_treemap input for this report only.
5. Do not modify deterministic aliases or merge concepts globally.

Return JSON only with:
{
  "schema_version": "theme_candidate_resolution_result.v1",
  "decisions": [
    {
      "decision": "resolved|unresolved",
      "alias_key": "...",
      "concept_id": "...",
      "paper_ids": ["..."],
      "evidence": ["..."]
    }
  ]
}
"""


def theme_treemap_needs_candidate_resolution(
    raw_theme_treemap: Mapping[str, Any] | None,
    papers: Iterable[Any] | None,
) -> bool:
    return _candidate_resolution_trigger_reason(raw_theme_treemap, papers) != ""


def build_theme_candidate_resolution_request(
    raw_theme_treemap: Mapping[str, Any] | None,
    papers: Iterable[Any] | None,
    *,
    display_query: str = "",
    language: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    reason = _candidate_resolution_trigger_reason(raw_theme_treemap, papers)
    paper_list = list(papers or [])
    if not reason:
        return {}, _trace(attempted=False, applied=False, reason="skipped_deterministic_enough")

    request_papers = [_paper_payload(paper, index) for index, paper in enumerate(paper_list, 1)]
    alias_map: dict[str, dict[str, Any]] = {}
    for index, paper in enumerate(paper_list, 1):
        paper_id = _paper_id(paper, index)
        for match in _ambiguous_candidate_matches(paper, paper_id=paper_id):
            alias_key = str(match.get("alias_key") or "")
            if not alias_key:
                continue
            entry = alias_map.setdefault(
                alias_key,
                {
                    "alias_key": alias_key,
                    "surface": str(match.get("surface") or _surface_from_alias_key(alias_key)),
                    "paper_ids": [],
                    "candidates": {},
                },
            )
            for matched_paper_id in match.get("paper_ids") or [paper_id]:
                matched_paper_id = str(matched_paper_id)
                if matched_paper_id and matched_paper_id not in entry["paper_ids"]:
                    entry["paper_ids"].append(matched_paper_id)
            for candidate in match.get("candidates") or []:
                if not isinstance(candidate, Mapping):
                    continue
                concept_id = str(candidate.get("concept_id") or "")
                if not concept_id:
                    continue
                entry["candidates"].setdefault(concept_id, _candidate_request_payload(candidate))

    candidate_aliases = []
    for entry in alias_map.values():
        candidates = list(entry["candidates"].values())
        if not candidates or not entry["paper_ids"]:
            continue
        candidates.sort(key=lambda candidate: (-int(candidate.get("specificity") or 0), str(candidate.get("concept_id") or "")))
        candidate_aliases.append(
            {
                "alias_key": entry["alias_key"],
                "surface": entry["surface"],
                "paper_ids": sorted(entry["paper_ids"]),
                "candidates": candidates,
            }
        )
    candidate_aliases.sort(key=lambda entry: (-len(entry["paper_ids"]), str(entry["alias_key"])))

    if not candidate_aliases:
        return {}, _trace(attempted=False, applied=False, reason="skipped_no_ambiguous_candidates", trigger_reason=reason)

    request = {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "trigger_reason": reason,
        "display_query": display_query or "",
        "language": language or "",
        "papers": request_papers,
        "candidate_aliases": candidate_aliases,
    }
    return request, _trace(
        attempted=False,
        applied=False,
        reason="agent_resolution_not_supplied",
        trigger_reason=reason,
    )


def apply_theme_candidate_resolution_result(
    raw_theme_treemap: Mapping[str, Any] | None,
    request: Mapping[str, Any] | None,
    result: Mapping[str, Any] | None,
    *,
    model_label: str = "host-agent",
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = _clone_theme_treemap(raw_theme_treemap)
    if not isinstance(request, Mapping) or not request.get("candidate_aliases"):
        return raw, _trace(attempted=False, applied=False, reason="request_not_available")
    if not isinstance(result, Mapping):
        return raw, _trace(attempted=False, applied=False, reason="agent_resolution_not_supplied")
    decisions = result.get("decisions")
    if not isinstance(decisions, list):
        return raw, _trace(attempted=True, applied=False, reason="invalid_result", model=model_label)

    request_index = _request_index(request)
    resolved_by_concept: dict[str, dict[str, Any]] = {}
    resolved_count = 0
    unresolved_count = 0
    for decision in decisions:
        if not isinstance(decision, Mapping):
            unresolved_count += 1
            continue
        status = str(decision.get("decision") or "")
        if status != "resolved":
            unresolved_count += 1
            continue
        normalized = _normalize_resolved_decision(decision, request_index)
        if normalized is None:
            unresolved_count += 1
            continue
        concept_id = normalized["concept_id"]
        entry = resolved_by_concept.setdefault(
            concept_id,
            {
                "concept": normalized["concept"],
                "paper_ids": set(),
                "matched_aliases": defaultdict(set),
                "evidence": [],
                "confidence": set(),
            },
        )
        entry["paper_ids"].update(normalized["paper_ids"])
        entry["matched_aliases"][normalized["lang"]].add(normalized["surface"])
        entry["evidence"].extend(normalized["evidence"])
        if normalized.get("confidence"):
            entry["confidence"].add(normalized["confidence"])
        resolved_count += 1

    if not resolved_by_concept:
        return raw, _trace(
            attempted=True,
            applied=False,
            reason="no_valid_resolved_candidates",
            resolved_count=0,
            unresolved_count=unresolved_count,
            model=model_label,
        )

    refined = _merge_resolved_themes(raw, resolved_by_concept)
    return refined, _trace(
        attempted=True,
        applied=True,
        reason="applied",
        resolved_count=resolved_count,
        unresolved_count=unresolved_count,
        model=model_label,
        trigger_reason=str(request.get("trigger_reason") or ""),
    )


def _candidate_resolution_trigger_reason(
    raw_theme_treemap: Mapping[str, Any] | None,
    papers: Iterable[Any] | None,
) -> str:
    raw = raw_theme_treemap if isinstance(raw_theme_treemap, Mapping) else {}
    themes = _effective_themes(raw)
    status = str(raw.get("status") or "")
    if not themes or status in {LOW_SIGNAL_STATUS, RAW_LOW_SIGNAL_STATUS}:
        return "no_hit"

    paper_list = list(papers or [])
    total_papers = len(paper_list) or int(raw.get("total_papers") or 0)
    if total_papers < 3:
        return ""
    if len(themes) < 2:
        return "insufficient_hit"
    if all(int(theme.get("value") or 0) <= 1 for theme in themes):
        return "insufficient_hit"
    deterministic_paper_ids = {
        str(paper_id)
        for theme in themes
        if theme.get("concept_id")
        for paper_id in (theme.get("paper_ids") or [])
        if paper_id
    }
    if deterministic_paper_ids and len(deterministic_paper_ids) < min(2, ceil(total_papers * 0.2)):
        return "insufficient_hit"
    return ""


def _clone_theme_treemap(theme_treemap: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(theme_treemap, Mapping):
        return {"themes": [], "total_papers": 0}
    return copy.deepcopy(dict(theme_treemap))


def _effective_themes(theme_treemap: Mapping[str, Any]) -> list[dict[str, Any]]:
    themes: list[dict[str, Any]] = []
    for theme in theme_treemap.get("themes") or []:
        if not isinstance(theme, Mapping):
            continue
        if str(theme.get("name") or "").strip() and int(theme.get("value") or 0) > 0:
            themes.append(dict(theme))
    return themes


def _paper_get(paper: Any, key: str) -> Any:
    if isinstance(paper, Mapping):
        return paper.get(key)
    return getattr(paper, key, None)


def _paper_id(paper: Any, index: int) -> str:
    return str(_paper_get(paper, "paper_id") or _paper_get(paper, "id") or f"paper-{index}")


def _paper_payload(paper: Any, index: int) -> dict[str, Any]:
    keywords = _paper_get(paper, "keywords") or []
    if not isinstance(keywords, list):
        keywords = [str(keywords)]
    return {
        "paper_id": _paper_id(paper, index),
        "title": str(_paper_get(paper, "title") or ""),
        "abstract": str(_paper_get(paper, "abstract") or ""),
        "keywords": [str(keyword) for keyword in keywords if keyword],
    }


def _surface_from_alias_key(alias_key: str) -> str:
    return str(alias_key).split(":", 1)[1] if ":" in str(alias_key) else str(alias_key)


def _candidate_request_payload(candidate: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        "concept_id": str(candidate.get("concept_id") or ""),
        "canonical": dict(candidate.get("canonical") or {}),
        "domains": [str(value) for value in candidate.get("domains") or []],
        "parents": [str(value) for value in candidate.get("parents") or []],
        "specificity": int(candidate.get("specificity") or 0),
        "candidate_type": str(candidate.get("candidate_type") or ""),
        "risk_tags": [str(value) for value in candidate.get("risk_tags") or []],
        "reason": str(candidate.get("reason") or "blocked candidate; requires paper context"),
    }
    for key in ("source_concept_id", "target_hint", "resolution_group"):
        value = candidate.get(key)
        if value:
            payload[key] = value
    if "requires_context" in candidate:
        payload["requires_context"] = bool(candidate.get("requires_context"))
    if "allow_deterministic_shadow" in candidate:
        payload["allow_deterministic_shadow"] = bool(candidate.get("allow_deterministic_shadow"))
    evidence_aliases = [
        {"lang": str(item.get("lang") or ""), "alias": str(item.get("alias") or "")}
        for item in candidate.get("evidence_aliases") or []
        if isinstance(item, Mapping) and item.get("alias")
    ]
    if evidence_aliases:
        payload["evidence_aliases"] = evidence_aliases
    return payload


def _request_index(request: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for alias_entry in request.get("candidate_aliases") or []:
        if not isinstance(alias_entry, Mapping):
            continue
        alias_key = str(alias_entry.get("alias_key") or "")
        candidate_map = {
            str(candidate.get("concept_id") or ""): dict(candidate)
            for candidate in alias_entry.get("candidates") or []
            if isinstance(candidate, Mapping) and candidate.get("concept_id")
        }
        if alias_key and candidate_map:
            index[alias_key] = {
                "surface": str(alias_entry.get("surface") or _surface_from_alias_key(alias_key)),
                "paper_ids": {str(paper_id) for paper_id in alias_entry.get("paper_ids") or []},
                "candidates": candidate_map,
            }
    return index


def _normalize_resolved_decision(
    decision: Mapping[str, Any],
    request_index: Mapping[str, dict[str, Any]],
) -> dict[str, Any] | None:
    alias_key = str(decision.get("alias_key") or "")
    concept_id = str(decision.get("concept_id") or "")
    request_entry = request_index.get(alias_key)
    if not request_entry or concept_id not in request_entry["candidates"]:
        return None
    evidence = [str(item).strip() for item in decision.get("evidence") or [] if str(item).strip()]
    if not evidence:
        return None
    paper_ids = [str(paper_id) for paper_id in decision.get("paper_ids") or [] if str(paper_id)]
    if not paper_ids or not set(paper_ids).issubset(request_entry["paper_ids"]):
        return None
    return {
        "alias_key": alias_key,
        "lang": alias_key.split(":", 1)[0] if ":" in alias_key else "",
        "surface": str(decision.get("surface") or request_entry["surface"]),
        "concept_id": concept_id,
        "concept": request_entry["candidates"][concept_id],
        "paper_ids": paper_ids,
        "evidence": evidence,
        "confidence": str(decision.get("confidence") or ""),
    }


def _merge_resolved_themes(
    raw_theme_treemap: Mapping[str, Any],
    resolved_by_concept: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    refined = _clone_theme_treemap(raw_theme_treemap)
    existing: dict[str, dict[str, Any]] = {}
    output_themes: list[dict[str, Any]] = []
    for theme in refined.get("themes") or []:
        if not isinstance(theme, Mapping):
            continue
        copied = copy.deepcopy(dict(theme))
        concept_id = str(copied.get("concept_id") or "")
        if concept_id:
            existing[concept_id] = copied
        output_themes.append(copied)

    for concept_id, data in resolved_by_concept.items():
        target = existing.get(concept_id)
        if target is None:
            target = {
                "name": _concept_label(data["concept"]),
                "concept_id": concept_id,
                "method": "agent_resolved_ambiguous_alias",
                "source": "ambiguous_candidate_resolution",
            }
            output_themes.append(target)
        paper_ids = _ordered_union(target.get("paper_ids") or [], sorted(data["paper_ids"]))
        target["paper_ids"] = paper_ids
        target["value"] = len(paper_ids)
        matched_aliases = {
            str(lang): set(values)
            for lang, values in (target.get("matched_aliases") or {}).items()
            if isinstance(values, (list, set, tuple))
        }
        for lang, values in data["matched_aliases"].items():
            matched_aliases.setdefault(str(lang), set()).update(values)
        target["matched_aliases"] = {lang: sorted(values) for lang, values in matched_aliases.items() if values}
        evidence = _ordered_union(target.get("evidence") or [], data["evidence"])
        if evidence:
            target["evidence"] = evidence
        confidences = {value for value in data["confidence"] if value}
        if confidences:
            target["confidence"] = sorted(confidences)[-1]
        target.setdefault("method", "agent_resolved_ambiguous_alias")
        target.setdefault("source", "ambiguous_candidate_resolution")

    specificity_by_concept = {
        concept_id: int(data["concept"].get("specificity") or 0)
        for concept_id, data in resolved_by_concept.items()
    }
    output_themes.sort(
        key=lambda theme: (
            -int(theme.get("value") or 0),
            -specificity_by_concept.get(str(theme.get("concept_id") or ""), 0),
            str(theme.get("name") or ""),
        )
    )
    refined["themes"] = output_themes
    refined["method"] = _append_method(str(refined.get("method") or ""), "ambiguous_candidate_resolution")
    return refined


def _concept_label(concept: Mapping[str, Any]) -> str:
    canonical = concept.get("canonical") if isinstance(concept.get("canonical"), Mapping) else {}
    en = str(canonical.get("en") or "").strip()
    zh = str(canonical.get("zh") or "").strip()
    if en and zh:
        return f"{en} / {zh}"
    return zh or en or str(concept.get("concept_id") or "")


def _ordered_union(first: Iterable[Any], second: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for value in list(first or []) + list(second or []):
        text = str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        values.append(text)
    return values


def _append_method(base: str, suffix: str) -> str:
    if not base:
        return suffix
    if suffix in base.split("+"):
        return base
    return f"{base}+{suffix}"


def _trace(
    *,
    attempted: bool,
    applied: bool,
    reason: str,
    resolved_count: int | None = None,
    unresolved_count: int | None = None,
    trigger_reason: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    trace: dict[str, Any] = {
        "attempted": attempted,
        "applied": applied,
        "reason": reason,
    }
    if resolved_count is not None:
        trace["resolved_count"] = resolved_count
    if unresolved_count is not None:
        trace["unresolved_count"] = unresolved_count
    if trigger_reason:
        trace["trigger_reason"] = trigger_reason
    if model:
        trace["model"] = model
    return trace
