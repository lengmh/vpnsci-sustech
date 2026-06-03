"""Report recovery classification and quality policy helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .sources.search_cache import SearchSession, new_session_id
from .sources.search_models import coerce_search_hit


@dataclass
class ReportRecoveryDecision:
    recovery_kind: str
    capability: str
    reason: str


def classify_report_recovery(
    *,
    sidecar: Path | None = None,
    local_files: list[Path] | None = None,
    report_json: Path | None = None,
) -> ReportRecoveryDecision:
    """Classify available recovery materials using A/C/B semantics."""

    if sidecar and sidecar.exists():
        return ReportRecoveryDecision(
            recovery_kind="A",
            capability="standard",
            reason="sidecar_available",
        )
    if local_files:
        existing = [path for path in local_files if Path(path).exists()]
        if existing:
            return ReportRecoveryDecision(
                recovery_kind="C",
                capability="degraded",
                reason="weak_local_files_only",
            )
    if report_json and report_json.exists():
        return ReportRecoveryDecision(
            recovery_kind="B",
            capability="compatible",
            reason="legacy_report_json_available",
        )
    return ReportRecoveryDecision(
        recovery_kind="none",
        capability="unavailable",
        reason="no_recovery_material",
    )


def recover_session_from_download_sidecar(sidecar: dict | str | Path) -> SearchSession:
    """Build a weak-recovery SearchSession from a sidecar payload."""

    if isinstance(sidecar, (str, Path)):
        data = json.loads(Path(sidecar).read_text(encoding="utf-8"))
    else:
        data = dict(sidecar or {})
    items = [coerce_search_hit(item) for item in data.get("items", [])]
    root_session_id = data.get("root_session_id") or ""
    source_session_id = data.get("source_session_id") or root_session_id or ""
    return SearchSession(
        session_id=new_session_id(),
        query=data.get("original_query") or "",
        filters={"recovered_from": "download_sidecar"},
        hits=items,
        origin={"engine": "cnki", "kind": "weak_recovery"},
        derivation={
            "source_session_id": source_session_id,
            "root_session_id": root_session_id or source_session_id,
            "derivation_type": "download_sidecar_recovery",
            "selected_count_before": len(items),
            "selected_count_after": len(items),
        },
        display_query=data.get("display_query") or "",
        recovered_label=data.get("recovered_label") or data.get("display_query") or "",
        source_summary={"cnki": len(items)} if items else {},
    )


def split_missing_and_insufficient_fields(
    *,
    total_hits: int,
    field_presence: dict[str, int],
) -> tuple[list[str], list[str]]:
    """Separate missing fields from insufficient-but-present fields."""

    missing: list[str] = []
    insufficient: list[str] = []
    for field, count in (field_presence or {}).items():
        value = int(count or 0)
        if value <= 0:
            missing.append(field)
            continue
        if field == "citation_count" and value < 5:
            insufficient.append(field)
    return missing, insufficient


def infer_quality_profile(
    *,
    origin_kind: str,
    actual_queries: list[dict],
    total_hits: int,
    field_presence: dict[str, int],
    original_query: str,
    display_query: str,
    recovered_label: str,
) -> dict:
    """Build the minimal quality profile used by degraded-report policy."""

    if origin_kind == "source_execution":
        query_trace_level = "exact"
        audit_level = "full"
    elif origin_kind == "html_import":
        query_trace_level = "imported"
        audit_level = "limited"
    else:
        query_trace_level = "recovered" if (display_query or recovered_label) else "missing"
        audit_level = "minimal"

    if original_query:
        title_mode = "search"
    elif display_query:
        title_mode = "summary"
    else:
        title_mode = "recovered_summary"

    if origin_kind == "source_execution" and actual_queries:
        query_strip_mode = "actual_queries"
    elif origin_kind == "html_import" and actual_queries:
        query_strip_mode = "imported_queries"
    else:
        query_strip_mode = "hidden"

    discovery_curve_mode = (
        "enabled"
        if origin_kind == "source_execution" and actual_queries and total_hits >= 8
        else "disabled"
    )

    citation_count_points = int((field_presence or {}).get("citation_count") or 0)
    year_points = int((field_presence or {}).get("year") or 0)
    citation_analysis_mode = "enabled" if min(citation_count_points, year_points) >= 5 else "disabled"

    thematic_points = int((field_presence or {}).get("abstract_or_keywords") or 0)
    if total_hits and thematic_points / total_hits >= 0.6:
        topic_analysis_mode = "enabled"
    elif thematic_points > 0:
        topic_analysis_mode = "limited"
    else:
        topic_analysis_mode = "disabled"

    return {
        "query_trace_level": query_trace_level,
        "audit_level": audit_level,
        "title_mode": title_mode,
        "query_strip_mode": query_strip_mode,
        "discovery_curve_mode": discovery_curve_mode,
        "citation_analysis_mode": citation_analysis_mode,
        "topic_analysis_mode": topic_analysis_mode,
    }
