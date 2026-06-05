"""Report recovery classification and quality policy helpers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path

from .sources.search_cache import SearchSession, new_session_id
from .sources.search_models import SearchHit, coerce_search_hit


LEGACY_REPORT_FILENAMES = {
    "metadata.json",
    "paper_list.json",
    "report_data.json",
    "prisma_log.json",
}
RECOVERY_LOCAL_CNKI_EXTENSIONS = {"pdf", "caj", "cajx", "nh", "kdh"}


@dataclass
class ReportRecoveryDecision:
    recovery_kind: str
    capability: str
    reason: str
    details: dict = field(default_factory=dict)


@dataclass
class ResolvedReportRecovery:
    session: SearchSession
    decision: ReportRecoveryDecision


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
    """Build a SearchSession from a formal download-workflow sidecar payload."""

    if isinstance(sidecar, (str, Path)):
        data = json.loads(Path(sidecar).read_text(encoding="utf-8"))
    else:
        data = dict(sidecar or {})
    items = [coerce_search_hit(item) for item in data.get("items", [])]
    root_session_id = data.get("root_session_id") or ""
    source_session_id = data.get("source_session_id") or root_session_id or ""
    derived_session_id = data.get("derived_session_id") or ""
    display_query = data.get("display_query") or ""
    recovered_label = data.get("recovered_label") or display_query or ""
    missing_fields = [str(item) for item in (data.get("missing_fields") or []) if item]
    requested_capability = data.get("report_recovery_capability") or "standard"
    capability = "degraded" if missing_fields else requested_capability
    source_summary = _source_summary_from_hits(items)
    return SearchSession(
        session_id=new_session_id(),
        query=data.get("original_query") or "",
        filters={
            "recovered_from": "download_sidecar",
            "workflow_id": data.get("workflow_id") or "",
        },
        hits=items,
        origin={
            "engine": "cnki",
            "kind": "download_sidecar",
            "report_recovery_capability": capability,
            "runner": data.get("runner") or "agent",
            "missing_fields": missing_fields,
        },
        derivation={
            "source_session_id": source_session_id,
            "root_session_id": root_session_id or source_session_id,
            "derived_session_id": derived_session_id,
            "derivation_type": "download_sidecar_recovery",
            "selected_count_before": len(items),
            "selected_count_after": len(items),
        },
        display_query=display_query,
        recovered_label=recovered_label,
        source_summary=source_summary,
    )


def recover_session_from_legacy_report_json(report_json: dict | str | Path) -> SearchSession:
    """Build a SearchSession from legacy materialized report JSON files."""

    bundle = _load_legacy_report_bundle(report_json)
    metadata = bundle["metadata"]
    papers = bundle["paper_list"]
    hits = [_legacy_paper_to_hit(paper) for paper in papers]
    original_query = metadata.get("original_query") or metadata.get("seed_session_query") or ""
    display_query = metadata.get("display_query") or (metadata.get("query") if not original_query else "") or ""
    recovered_label = metadata.get("recovered_label") or (
        metadata.get("query") if not original_query and not display_query else ""
    )
    source_session_id = metadata.get("seed_session_id") or metadata.get("search_id") or ""
    origin_kind = _legacy_origin_kind(metadata)
    engine = _legacy_engine(metadata, hits)
    source_summary = metadata.get("source_summary") or _source_summary_from_hits(hits)
    return SearchSession(
        session_id=new_session_id(),
        query=original_query,
        filters={
            "recovered_from": "legacy_report_json",
            "report_json": str(bundle["report_json_path"]),
        },
        hits=hits,
        origin={
            "engine": engine,
            "kind": origin_kind,
            "report_recovery_capability": "compatible",
        },
        derivation={
            "source_session_id": source_session_id,
            "root_session_id": source_session_id,
            "derivation_type": "legacy_report_recovery",
            "selected_count_before": len(hits),
            "selected_count_after": len(hits),
        },
        display_query=display_query,
        recovered_label=recovered_label,
        source_summary=source_summary,
        created_at=metadata.get("generated_at") or datetime.now(timezone.utc).isoformat(),
    )


def recover_session_from_local_files(
    local_files: list[str | Path],
    *,
    display_query: str = "",
    recovered_label: str = "",
) -> SearchSession:
    """Build a weak-recovery SearchSession from local files only."""

    existing = [Path(path) for path in (local_files or []) if Path(path).exists()]
    if not existing:
        raise FileNotFoundError("No local files available for weak recovery.")
    hits = [_local_file_to_hit(path) for path in existing]
    normalized_display = display_query or ""
    normalized_recovered = recovered_label or ("" if normalized_display else "Recovered local files")
    return SearchSession(
        session_id=new_session_id(),
        query="",
        filters={"recovered_from": "local_files"},
        hits=hits,
        origin={"engine": "cnki", "kind": "weak_recovery", "report_recovery_capability": "degraded"},
        derivation={
            "source_session_id": "",
            "root_session_id": "",
            "derivation_type": "weak_local_file_recovery",
            "selected_count_before": len(hits),
            "selected_count_after": len(hits),
        },
        display_query=normalized_display,
        recovered_label=normalized_recovered,
        source_summary=_source_summary_from_hits(hits),
    )


def resolve_report_recovery_session(
    *,
    sidecar: str | Path | None = None,
    local_files: list[str | Path] | None = None,
    report_json: str | Path | None = None,
    display_query: str = "",
    recovered_label: str = "",
    prefer: str = "auto",
) -> ResolvedReportRecovery:
    """Resolve A/B/C recovery materials into one SearchSession."""

    sidecar_path = Path(sidecar) if sidecar else None
    report_json_path = _normalize_legacy_report_path(report_json)
    local_file_paths = [Path(path) for path in (local_files or []) if Path(path).exists()]
    preferred = _normalize_recovery_preference(prefer)

    has_sidecar = bool(sidecar_path and sidecar_path.exists())
    has_report_json = bool(report_json_path and report_json_path.exists())
    has_local_files = bool(local_file_paths)

    if preferred == "A":
        if not has_sidecar:
            raise FileNotFoundError("Requested A recovery, but sidecar was not found.")
        session = recover_session_from_download_sidecar(sidecar_path)
        decision = ReportRecoveryDecision("A", _sidecar_capability(session), "sidecar_available")
    elif preferred == "B":
        if not has_report_json:
            raise FileNotFoundError("Requested B recovery, but report_json was not found.")
        session = recover_session_from_legacy_report_json(report_json_path)
        decision = ReportRecoveryDecision("B", "compatible", "legacy_report_json_available")
    elif preferred == "C":
        if not has_local_files:
            raise FileNotFoundError("Requested C recovery, but local_files were not found.")
        session = recover_session_from_local_files(
            local_file_paths,
            display_query=display_query,
            recovered_label=recovered_label,
        )
        decision = ReportRecoveryDecision("C", "degraded", "weak_local_files_only")
    else:
        if has_sidecar:
            session = recover_session_from_download_sidecar(sidecar_path)
            decision = ReportRecoveryDecision("A", _sidecar_capability(session), "sidecar_available")
        elif has_local_files:
            session = recover_session_from_local_files(
                local_file_paths,
                display_query=display_query,
                recovered_label=recovered_label,
            )
            decision = ReportRecoveryDecision("C", "degraded", "weak_local_files_only")
        elif has_report_json:
            session = recover_session_from_legacy_report_json(report_json_path)
            decision = ReportRecoveryDecision("B", "compatible", "legacy_report_json_available")
        else:
            raise FileNotFoundError("No recovery material found.")

    details: dict = {}
    if has_sidecar and has_report_json:
        details.update(_compare_recovery_candidates(sidecar_path, report_json_path))
    if has_local_files:
        details["local_file_count"] = len(local_file_paths)
    if details:
        decision.details = details
    return ResolvedReportRecovery(session=session, decision=decision)


def _source_summary_from_hits(hits: list[SearchHit]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for hit in hits:
        source_names = hit.sources or [hit.source or hit.backend or "unknown"]
        for source in source_names:
            counts[source] += 1
    return dict(counts)


def _sidecar_capability(session: SearchSession) -> str:
    origin = session.origin if isinstance(session.origin, dict) else {}
    capability = str(origin.get("report_recovery_capability") or "standard")
    return "degraded" if capability != "standard" else "standard"


def _normalize_recovery_preference(prefer: str) -> str:
    value = (prefer or "auto").strip().upper()
    if value in {"AUTO", "A", "B", "C"}:
        return value
    raise ValueError(f"Unsupported recovery preference: {prefer}")


def _normalize_legacy_report_path(report_json: str | Path | None) -> Path | None:
    if not report_json:
        return None
    path = Path(report_json)
    if path.is_dir():
        for name in ("report_data.json", "metadata.json", "paper_list.json", "prisma_log.json"):
            candidate = path / name
            if candidate.exists():
                return candidate
        return path / "report_data.json"
    if path.name in LEGACY_REPORT_FILENAMES:
        return path
    return path


def _load_legacy_report_bundle(report_json: dict | str | Path) -> dict:
    if isinstance(report_json, dict):
        metadata = dict(report_json.get("metadata") or {})
        paper_list = list(report_json.get("paper_list") or [])
        return {
            "metadata": metadata,
            "paper_list": paper_list,
            "report_json_path": Path("<memory>"),
        }

    normalized = _normalize_legacy_report_path(report_json)
    if normalized is None:
        raise FileNotFoundError("Missing legacy report JSON path.")
    base_dir = normalized if normalized.is_dir() else normalized.parent

    report_data = _read_json_if_exists(base_dir / "report_data.json")
    metadata = report_data.get("metadata") if isinstance(report_data, dict) else None
    paper_list = report_data.get("paper_list") if isinstance(report_data, dict) else None

    if normalized.name == "metadata.json":
        metadata = _read_json_if_exists(normalized) or metadata
    elif normalized.name == "paper_list.json":
        paper_list = _read_json_if_exists(normalized) or paper_list
    elif normalized.name == "prisma_log.json":
        _ = _read_json_if_exists(normalized)
    elif normalized.name == "report_data.json":
        report_data = _read_json_if_exists(normalized) or report_data
        if isinstance(report_data, dict):
            metadata = report_data.get("metadata") or metadata
            paper_list = report_data.get("paper_list") or paper_list

    metadata = metadata or _read_json_if_exists(base_dir / "metadata.json") or {}
    paper_list = paper_list or _read_json_if_exists(base_dir / "paper_list.json") or []
    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(paper_list, list):
        paper_list = []
    return {
        "metadata": metadata,
        "paper_list": paper_list,
        "report_json_path": normalized,
    }


def _read_json_if_exists(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _legacy_paper_to_hit(paper: dict) -> SearchHit:
    authors = paper.get("authors") or paper.get("authors_full") or []
    if isinstance(authors, str):
        authors = [part.strip() for part in authors.split(",") if part.strip()]
    raw_sources = paper.get("sources")
    if isinstance(raw_sources, list):
        sources = [str(item) for item in raw_sources if item]
    else:
        source_value = paper.get("source") or ""
        sources = [part.strip() for part in str(source_value).split(",") if part.strip()]
    return coerce_search_hit(
        {
            "hit_key": paper.get("paper_id") or paper.get("id") or "",
            "title": paper.get("title") or "",
            "doi": paper.get("doi") or "",
            "url": paper.get("url") or "",
            "pdf_url": paper.get("pdf_url") or "",
            "journal": paper.get("venue") or paper.get("journal") or "",
            "year": paper.get("year"),
            "authors": authors,
            "citation_count": int(paper.get("citation_count") or 0),
            "abstract": paper.get("abstract") or "",
            "cnki_id": paper.get("cnki_id") or "",
            "dbcode": paper.get("dbcode") or "",
            "dbname": paper.get("dbname") or "",
            "source_url": paper.get("source_url") or "",
            "download_format": paper.get("download_format") or "",
            "local_file": paper.get("local_file") or "",
            "result_type": paper.get("result_type") or "",
            "keywords": paper.get("keywords") or [],
            "affiliations": paper.get("affiliations") or [],
            "source": sources[0] if sources else (paper.get("source") or ""),
            "backend": sources[0] if sources else (paper.get("source") or ""),
            "sources": sources,
        }
    )


def _legacy_origin_kind(metadata: dict) -> str:
    quality = metadata.get("quality_profile") or {}
    trace_level = quality.get("query_trace_level") or ""
    if trace_level == "exact":
        return "source_execution"
    if trace_level == "imported":
        return "html_import"
    if trace_level in {"recovered", "missing"}:
        return "weak_recovery"
    return "legacy_report_json"


def _legacy_engine(metadata: dict, hits: list[SearchHit]) -> str:
    seed_source = (metadata.get("seed_source") or "").strip()
    if seed_source:
        return seed_source
    summary = metadata.get("source_summary") or {}
    if len(summary) == 1:
        return next(iter(summary))
    if hits:
        first = hits[0]
        return first.source or first.backend or "legacy"
    return "legacy"


def _local_file_to_hit(path: Path) -> SearchHit:
    ext = path.suffix.lower().lstrip(".")
    source = "cnki" if ext in RECOVERY_LOCAL_CNKI_EXTENSIONS else "local_file"
    return coerce_search_hit(
        {
            "title": path.stem,
            "local_file": str(path),
            "download_format": ext,
            "result_type": f"local_{ext}" if ext else "local_file",
            "source": source,
            "backend": source,
            "sources": [source],
        }
    )


def _compare_recovery_candidates(sidecar_path: Path, report_json_path: Path) -> dict:
    sidecar_session = recover_session_from_download_sidecar(sidecar_path)
    legacy_session = recover_session_from_legacy_report_json(report_json_path)
    sidecar_keys = {hit.hit_key for hit in sidecar_session.hits if hit.hit_key}
    legacy_keys = {hit.hit_key for hit in legacy_session.hits if hit.hit_key}
    identity_match = bool(sidecar_keys and legacy_keys and sidecar_keys == legacy_keys)
    freshness_winner = _compare_freshness(sidecar_path, report_json_path)
    return {
        "identity_match": identity_match,
        "sidecar_hit_count": len(sidecar_keys),
        "legacy_hit_count": len(legacy_keys),
        "freshness_winner": freshness_winner,
    }


def _compare_freshness(sidecar_path: Path, report_json_path: Path) -> str:
    sidecar_time = _extract_candidate_time(sidecar_path, "created_at")
    legacy_time = _extract_candidate_time(report_json_path, "generated_at")
    if sidecar_time and legacy_time:
        if sidecar_time > legacy_time:
            return "sidecar"
        if legacy_time > sidecar_time:
            return "legacy"
        return "same"
    return "unknown"


def _extract_candidate_time(path: Path, field_name: str) -> datetime | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if field_name == "generated_at" and isinstance(payload, dict) and "metadata" in payload:
        value = (payload.get("metadata") or {}).get("generated_at")
    else:
        value = payload.get(field_name) if isinstance(payload, dict) else None
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


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
    recovery_capability: str = "",
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
    elif origin_kind == "download_sidecar":
        query_trace_level = "recovered" if (display_query or recovered_label or original_query) else "missing"
        audit_level = "full" if (original_query or actual_queries) else "minimal"
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

    if origin_kind in {"source_execution", "download_sidecar"} and actual_queries:
        query_strip_mode = "actual_queries"
    elif origin_kind == "html_import" and actual_queries:
        query_strip_mode = "imported_queries"
    else:
        query_strip_mode = "hidden"

    capability = str(recovery_capability or "").strip().lower()
    discovery_curve_mode = (
        "enabled"
        if capability in {"", "standard"}
        and origin_kind in {"source_execution", "download_sidecar"}
        and actual_queries
        and total_hits >= 8
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
