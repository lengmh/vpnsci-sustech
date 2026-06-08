"""Tool-local deterministic helpers for agent-owned theme postprocess."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import copy
from typing import Any


THEME_POSTPROCESS_MAX_LABEL_LENGTH = 80
THEME_POSTPROCESS_MAX_REPRESENTATIVE_TITLES = 3

SYSTEM_PROMPT = """You are refining precomputed research-report theme labels.

Rules:
1. You may only normalize labels for existing themes.
2. You may merge obviously synonymous or abbreviation-expanded themes.
3. You must not invent unrelated new topics.
4. You must not remove evidence or reassign papers outside the provided theme indices.
5. Prefer concise, complete, publication-ready labels.
6. Ignore venue, school, proceedings, thesis, dissertation, and similar metadata noise.

Return JSON only with this shape:
{
  "groups": [
    {
      "label": "Normalized label",
      "theme_indices": [0, 2]
    }
  ]
}

Every provided theme index must appear exactly once across all groups.
"""


def build_theme_postprocess_request(
    raw_theme_treemap: Mapping[str, Any] | None,
    papers: Iterable[Any] | None = None,
    *,
    report_mode: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = _clone_theme_treemap(raw_theme_treemap)
    effective_themes = _effective_themes(raw)
    representative_titles = _representative_titles_by_theme(raw, papers)

    if len(effective_themes) < 2:
        return {}, _trace(attempted=False, applied=False, reason="skipped_insufficient_themes")
    if all(int(theme.get("value") or 0) <= 1 for theme in effective_themes):
        return {}, _trace(attempted=False, applied=False, reason="skipped_noninformative_values")
    if not any(representative_titles.get(index) for index in range(len(raw.get("themes") or []))):
        return {}, _trace(attempted=False, applied=False, reason="skipped_missing_titles")

    theme_payload = []
    for index, theme in enumerate(raw.get("themes") or []):
        if not isinstance(theme, Mapping):
            continue
        theme_payload.append(
            {
                "index": index,
                "name": str(theme.get("name") or "").strip(),
                "value": int(theme.get("value") or 0),
                "paper_ids": [str(paper_id) for paper_id in (theme.get("paper_ids") or []) if paper_id],
                "representative_titles": representative_titles.get(index) or [],
            }
        )

    return {
        "report_mode": report_mode or "",
        "agent_guidance": SYSTEM_PROMPT,
        "themes": theme_payload,
    }, _trace(attempted=False, applied=False, reason="agent_postprocess_not_supplied")


def apply_theme_postprocess_result(
    raw_theme_treemap: Mapping[str, Any] | None,
    result: Mapping[str, Any] | None,
    *,
    model_label: str = "agent-manual",
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = _clone_theme_treemap(raw_theme_treemap)
    if not isinstance(result, Mapping):
        return raw, _trace(attempted=False, applied=False, reason="agent_postprocess_not_supplied")

    groups = result.get("groups")
    if not isinstance(groups, list):
        return raw, _trace(attempted=True, applied=False, reason="invalid_mapping", model=model_label)

    try:
        normalized_groups = _normalize_groups(groups)
    except Exception:  # noqa: BLE001
        return raw, _trace(attempted=True, applied=False, reason="invalid_mapping", model=model_label)

    theme_count = len(raw.get("themes") or [])
    if not _groups_cover_all_indices(normalized_groups, theme_count):
        return raw, _trace(attempted=True, applied=False, reason="invalid_mapping", model=model_label)

    refined = _merge_theme_groups(raw, normalized_groups)
    applied = _theme_postprocess_changed(raw, refined)
    reason = "applied" if applied else "no_change"
    merge_count = max(0, theme_count - len(refined.get("themes") or []))
    return refined, _trace(
        attempted=True,
        applied=applied,
        reason=reason,
        merge_count=merge_count if applied else None,
        model=model_label,
    )


def _clone_theme_treemap(theme_treemap: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(theme_treemap, Mapping):
        return {"themes": [], "total_papers": 0}
    return copy.deepcopy(dict(theme_treemap))


def _effective_themes(theme_treemap: Mapping[str, Any]) -> list[dict[str, Any]]:
    themes = theme_treemap.get("themes") or []
    results: list[dict[str, Any]] = []
    for theme in themes:
        if not isinstance(theme, Mapping):
            continue
        name = str(theme.get("name") or "").strip()
        value = int(theme.get("value") or 0)
        if name and value > 0:
            results.append(dict(theme))
    return results


def _paper_get(paper: Any, key: str) -> Any:
    if isinstance(paper, Mapping):
        return paper.get(key)
    return getattr(paper, key, None)


def _representative_titles_by_theme(
    theme_treemap: Mapping[str, Any],
    papers: Iterable[Any] | None,
) -> dict[int, list[str]]:
    paper_map: dict[str, str] = {}
    for paper in papers or []:
        paper_id = _paper_get(paper, "paper_id") or _paper_get(paper, "id")
        title = _paper_get(paper, "title")
        if paper_id and title:
            paper_map[str(paper_id)] = str(title).strip()

    titles_by_theme: dict[int, list[str]] = {}
    for index, theme in enumerate(theme_treemap.get("themes") or []):
        if not isinstance(theme, Mapping):
            continue
        seen: set[str] = set()
        collected: list[str] = []
        for paper_id in theme.get("paper_ids") or []:
            title = paper_map.get(str(paper_id), "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            collected.append(title)
            if len(collected) >= THEME_POSTPROCESS_MAX_REPRESENTATIVE_TITLES:
                break
        titles_by_theme[index] = collected
    return titles_by_theme


def _normalize_groups(groups: list[Any]) -> list[dict[str, Any]]:
    normalized_groups: list[dict[str, Any]] = []
    for group in groups:
        if not isinstance(group, Mapping):
            raise ValueError("Theme group must be an object.")
        label = str(group.get("label") or "").strip()
        if not label or len(label) > THEME_POSTPROCESS_MAX_LABEL_LENGTH:
            raise ValueError("Theme label is empty or too long.")
        indices = group.get("theme_indices") or []
        if not isinstance(indices, list) or not indices:
            raise ValueError("theme_indices must be a non-empty list.")
        normalized_groups.append(
            {
                "label": label,
                "theme_indices": [int(index) for index in indices],
            }
        )
    return normalized_groups


def _groups_cover_all_indices(groups: list[dict[str, Any]], theme_count: int) -> bool:
    expected = set(range(theme_count))
    seen: list[int] = []
    for group in groups:
        indices = group.get("theme_indices") or []
        if any(index < 0 or index >= theme_count for index in indices):
            return False
        seen.extend(indices)
    return set(seen) == expected and len(seen) == theme_count


def _merge_theme_groups(
    raw_theme_treemap: Mapping[str, Any],
    groups: list[dict[str, Any]],
) -> dict[str, Any]:
    themes = list(raw_theme_treemap.get("themes") or [])
    refined_themes: list[dict[str, Any]] = []
    for group in groups:
        label = str(group["label"]).strip()
        theme_indices = [int(index) for index in group["theme_indices"]]
        union_ids: list[str] = []
        seen_ids: set[str] = set()
        fallback_value = 0
        for index in theme_indices:
            theme = themes[index]
            if not isinstance(theme, Mapping):
                continue
            fallback_value += int(theme.get("value") or 0)
            for paper_id in theme.get("paper_ids") or []:
                normalized_id = str(paper_id)
                if normalized_id in seen_ids:
                    continue
                seen_ids.add(normalized_id)
                union_ids.append(normalized_id)
        refined_themes.append(
            {
                "name": label,
                "value": len(union_ids) or fallback_value,
                "paper_ids": union_ids,
            }
        )

    refined_themes.sort(
        key=lambda theme: (-int(theme.get("value") or 0), str(theme.get("name") or "")),
    )
    refined = _clone_theme_treemap(raw_theme_treemap)
    refined["themes"] = refined_themes
    base_method = str(refined.get("method") or "").strip()
    refined["method"] = (
        f"{base_method}+agent_label_postprocess"
        if base_method
        else "agent_label_postprocess"
    )
    base_note = str(refined.get("note") or "").strip()
    suffix = " Display labels were normalized via a conservative agent-owned postprocess step."
    refined["note"] = f"{base_note}{suffix}".strip()
    return refined


def _theme_postprocess_changed(
    raw_theme_treemap: Mapping[str, Any],
    refined_theme_treemap: Mapping[str, Any],
) -> bool:
    raw_themes = raw_theme_treemap.get("themes") or []
    refined_themes = refined_theme_treemap.get("themes") or []
    if len(raw_themes) != len(refined_themes):
        return True
    for raw, refined in zip(raw_themes, refined_themes):
        if not isinstance(raw, Mapping) or not isinstance(refined, Mapping):
            return True
        if str(raw.get("name") or "").strip() != str(refined.get("name") or "").strip():
            return True
        if list(raw.get("paper_ids") or []) != list(refined.get("paper_ids") or []):
            return True
        if int(raw.get("value") or 0) != int(refined.get("value") or 0):
            return True
    return False


def _trace(
    *,
    attempted: bool,
    applied: bool,
    reason: str,
    merge_count: int | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    trace: dict[str, Any] = {
        "attempted": attempted,
        "applied": applied,
        "reason": reason,
    }
    if merge_count is not None:
        trace["merge_count"] = merge_count
    if model:
        trace["model"] = model
    return trace
