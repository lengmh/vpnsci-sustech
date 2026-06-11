"""Adapter that renders a vpnsci search session with bundled paper-search-pro assets."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import webbrowser

from .config import Config
from .report_recovery import infer_quality_profile, split_missing_and_insufficient_fields
from .sources.search_cache import SearchSession
from .sources.search_models import SearchHit, coerce_search_hit
from .theme_clustering import build_keyword_topic_themes, build_text_themes
from .theme_postprocess import (
    THEME_POSTPROCESS_REQUEST_FILENAME,
    THEME_POSTPROCESS_RESULT_FILENAME,
    apply_theme_postprocess_result,
    build_theme_postprocess_request,
)


RCS_CLASSIFICATION_REQUEST_FILENAME = "rcs_classification_request.json"
RCS_CLASSIFICATION_RESULT_FILENAME = "rcs_classification_result.json"


def render_html_webartifacts(*args, **kwargs):
    from scripts.html_renderer_webartifacts import render_html_webartifacts as renderer

    return renderer(*args, **kwargs)


def _detect_language(query: str) -> str:
    return "zh" if any("\u4e00" <= ch <= "\u9fff" for ch in query or "") else "en"


def _load_seed(path: Path) -> SearchSession:
    data = json.loads(path.read_text(encoding="utf-8"))
    return SearchSession(
        session_id=data["session_id"],
        query=data["query"],
        filters=data.get("filters") or {},
        hits=[coerce_search_hit(item) for item in data.get("hits", [])],
        schema_version=int(data.get("schema_version") or 2),
        origin=data.get("origin") or {},
        derivation=data.get("derivation") or {},
        display_query=(data.get("display_query") or data.get("query") or ""),
        recovered_label=data.get("recovered_label") or "",
        source_summary=data.get("source_summary") or {},
        errors=[],
        upgrade_suggested=bool(data.get("upgrade_suggested")),
        decision_reasons=data.get("decision_reasons") or [],
        created_at=data.get("created_at") or "",
    )


def _score_hit(hit: SearchHit) -> int:
    """Neutral seed-preview RCS for reports that skip formal classification.

    Domain-specific relevance terms must not live here. Reviewed concept aliases
    and future scoring/classification inputs belong in explicit data contracts,
    not hidden adapter heuristics.
    """

    return 5


SCAFFOLD_RCS = 5
SCAFFOLD_RCS_SOURCE = "scaffold"
SCAFFOLD_RCS_FLAG = "scaffold_neutral"
INVALID_RCS_FLAGS = {"parse_failed_uncertain"}


def _rcs_value_if_valid(paper: dict) -> int | None:
    if not paper.get("rcs_valid"):
        return None
    if paper.get("rcs_flag") in INVALID_RCS_FLAGS:
        return None
    try:
        rcs = int(paper.get("rcs"))
    except (TypeError, ValueError):
        return None
    if 0 <= rcs <= 10:
        return rcs
    return None


def _rcs_coverage_metadata(
    papers: list[dict],
    *,
    rcs_execution_mode: str = "none",
) -> dict:
    valid_count = sum(1 for paper in papers if _rcs_value_if_valid(paper) is not None)
    total_count = len(papers)
    execution_mode = rcs_execution_mode if rcs_execution_mode != "none" else "none"
    if valid_count == 0 and rcs_execution_mode == "none":
        notice = "RCS is unavailable for this report mode; formal RCS classification was not executed."
    elif valid_count == 0:
        notice = "Formal RCS classification was attempted, but no valid RCS scores were produced."
    elif execution_mode == "main_agent_serial":
        notice = "RCS covers the current seed paper set only; classification was executed serially by the main host Agent."
    else:
        notice = "RCS covers the current seed paper set only."
    return {
        "rcs_execution_mode": execution_mode if valid_count or rcs_execution_mode != "none" else "none",
        "rcs_scope": "none" if valid_count == 0 else "seed_set",
        "rcs_valid_count": valid_count,
        "rcs_total_count": total_count,
        "rcs_notice": notice,
    }


def _classification_records(result_payload: object) -> list[dict]:
    if isinstance(result_payload, dict):
        records = result_payload.get("papers") or result_payload.get("results")
    else:
        records = result_payload
    if not isinstance(records, list):
        raise ValueError("RCS classification result must be a JSON array or an object with papers/results.")
    if not all(isinstance(item, dict) for item in records):
        raise ValueError("Every RCS classification record must be an object.")
    return records


def _apply_rcs_classification_result(papers: list[dict], result_payload: object) -> list[dict]:
    records = _classification_records(result_payload)
    by_id = {
        str(paper.get("paper_id") or paper.get("id")): dict(paper)
        for paper in papers
    }
    if len(records) != len(by_id):
        raise ValueError("RCS classification result must cover every paper exactly once.")
    seen: set[str] = set()
    for record in records:
        paper_id = str(record.get("paper_id") or "")
        if not paper_id:
            raise ValueError("RCS classification record missing paper_id.")
        if paper_id in seen:
            raise ValueError(f"Duplicate RCS classification record for paper_id: {paper_id}")
        if paper_id not in by_id:
            raise ValueError(f"Unknown RCS classification paper_id: {paper_id}")
        seen.add(paper_id)
        try:
            rcs = int(record.get("rcs"))
        except (TypeError, ValueError):
            raise ValueError(f"Invalid RCS value for paper_id: {paper_id}") from None
        if rcs < 0 or rcs > 10:
            raise ValueError(f"RCS out of range for paper_id: {paper_id}")
        reasoning = str(record.get("reasoning") or "").strip()
        if not reasoning:
            raise ValueError(f"RCS classification record missing reasoning for paper_id: {paper_id}")
        flag = record.get("flag")
        flag_value = str(flag) if flag is not None else None
        valid = flag_value not in INVALID_RCS_FLAGS
        paper = by_id[paper_id]
        paper["rcs"] = rcs
        paper["rcs_reasoning"] = reasoning
        paper["rcs_valid"] = valid
        paper["rcs_source"] = "seed_classifier" if valid else "parser_fallback"
        paper["rcs_flag"] = flag_value
        by_id[paper_id] = paper
    return [by_id[str(paper.get("paper_id") or paper.get("id"))] for paper in papers]


def _build_rcs_classification_request(
    papers: list[dict],
    *,
    query: str,
    language: str,
    report_mode: str,
) -> dict:
    request_papers: list[dict] = []
    for paper in papers:
        request_papers.append(
            {
                "paper_id": paper.get("paper_id") or paper.get("id"),
                "title": paper.get("title") or "",
                "abstract": paper.get("abstract") or "",
                "keywords": paper.get("keywords") or [],
                "year": paper.get("year"),
                "venue": paper.get("venue") or "",
                "doi": paper.get("doi") or "",
                "source": paper.get("source") or "",
            }
        )
    return {
        "report_mode": report_mode,
        "rcs_scope": "seed_set",
        "classification_owner": "host_agent",
        "query": query,
        "language": language,
        "rubric_reference": "tools/paper-search-pro/references/rcs_rubric.md",
        "classifier_prompt_reference": "tools/paper-search-pro/references/classifier_subagent_prompt.md",
        "instructions": [
            "Apply the full paper-search-pro RCS rubric to this seed paper set only.",
            "Return JSON records only; do not run source expansion or PRISMA reconstruction.",
            "If classification runs in the main Agent instead of SubAgents, disclose rcs_execution_mode=main_agent_serial when applying the result.",
        ],
        "expected_output_schema": {
            "type": "array",
            "required": ["paper_id", "rcs", "reasoning"],
            "optional": ["flag"],
            "rcs_range": [0, 10],
        },
        "papers": request_papers,
    }


def _paper_id_from_hit(hit: SearchHit, index: int) -> str:
    if hit.hit_key:
        return hit.hit_key
    if hit.doi:
        return hit.doi
    if hit.cnki_id:
        return f"cnki:{hit.cnki_id}"
    return hit.openalex_id or hit.s2_paper_id or hit.url or hit.source_url or f"seed-{index}"


CNKI_SEED_FIELDS = ["cnki_id", "source_url", "download_format", "local_file", "result_type"]


def _seed_source_label(session: SearchSession) -> str:
    summary = session.source_summary or {}
    active = [source for source, count in summary.items() if count]
    if active == ["cnki"]:
        return "cnki"
    if active:
        return "mixed" if len(active) > 1 else active[0]
    hit_sources = {source for hit in session.hits for source in (hit.sources or [hit.source or hit.backend]) if source}
    if hit_sources == {"cnki"}:
        return "cnki"
    if hit_sources:
        return "mixed" if len(hit_sources) > 1 else next(iter(hit_sources))
    return "seed"


def _cnki_field_status(session: SearchSession) -> dict:
    cnki_hits = [
        hit for hit in session.hits
        if hit.cnki_id or hit.source_url or hit.download_format or hit.local_file or hit.result_type
        or "cnki" in (hit.sources or []) or hit.source == "cnki" or hit.backend == "cnki"
    ]
    preserved = {
        field: sum(1 for hit in cnki_hits if getattr(hit, field, ""))
        for field in CNKI_SEED_FIELDS
    }
    return {
        "present": bool(cnki_hits),
        "hit_count": len(cnki_hits),
        "fields": CNKI_SEED_FIELDS,
        "preserved_counts": preserved,
    }


def _paper_from_hit(hit: SearchHit, index: int, query: str) -> dict:
    rcs = _score_hit(hit)
    paper_id = _paper_id_from_hit(hit, index)
    paper_url = hit.url or hit.source_url
    return {
        "id": paper_id,
        "paper_id": paper_id,
        "title": hit.title,
        "authors_short": (
            ", ".join(hit.authors[:2])
            + (" et al." if len(hit.authors) > 2 else "")
            if hit.authors
            else ""
        ),
        "authors_full": hit.authors,
        "authors": hit.authors,
        "year": hit.year,
        "venue": hit.journal,
        "doi": hit.doi,
        "doi_url": f"https://doi.org/{hit.doi}" if hit.doi else paper_url,
        "url": paper_url,
        "pdf_url": hit.pdf_url,
        "abstract": hit.abstract,
        "citation_count": hit.citation_count,
        "cnki_id": hit.cnki_id,
        "dbcode": hit.dbcode,
        "dbname": hit.dbname,
        "source_url": hit.source_url,
        "download_format": hit.download_format,
        "local_file": hit.local_file,
        "result_type": hit.result_type,
        "keywords": hit.keywords,
        "affiliations": hit.affiliations,
        "source": ", ".join(hit.sources or [hit.source or hit.backend or "seed"]),
        "tier": "seed",
        "rcs": rcs,
        "rcs_reasoning": "Neutral scaffold value; formal RCS classification was not executed.",
        "rcs_valid": False,
        "rcs_source": SCAFFOLD_RCS_SOURCE,
        "rcs_flag": SCAFFOLD_RCS_FLAG,
        "discovery_path": f"query: {query}",
        "sources": hit.sources or [hit.source or hit.backend or "seed"],
    }


def _query_variants_from_session(session: SearchSession) -> list[dict]:
    variants: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add(variant_type: str, query: str) -> None:
        variant_type = variant_type or "unknown"
        query = query or ""
        if not query:
            return
        key = (variant_type, query)
        if key in seen:
            return
        seen.add(key)
        variants.append({"type": variant_type, "query": query})

    for hit in session.hits:
        add(hit.query_variant_type, hit.query_variant)
        for marker in hit.query_variants:
            if ":" in marker:
                variant_type, query = marker.split(":", 1)
                add(variant_type, query)
            else:
                add("unknown", marker)
    return variants


def _actual_query_groups_from_session(
    session: SearchSession,
    *,
    display_query: str = "",
) -> list[dict]:
    source_labels = {
        "openalex": "OpenAlex",
        "semantic_scholar": "Semantic Scholar",
        "semanticscholar": "Semantic Scholar",
        "s2": "Semantic Scholar",
        "crossref": "CrossRef",
        "pubmed": "PubMed",
        "arxiv": "arXiv",
        "vpnsci-search-session": "seed",
        "vpnsci_seed": "seed",
        "seed": "seed",
    }
    source_order = ["OpenAlex", "Semantic Scholar", "CrossRef", "PubMed", "arXiv", "seed"]
    user_query = (display_query or session.query or "").strip()
    groups: dict[str, list[str]] = {}

    def add(source: str, query: str) -> None:
        query = (query or "").strip()
        if not query:
            return
        raw_source = (source or "").strip().lower()
        label = source_labels.get(raw_source, source or "source")
        if label == "seed" and user_query and query == user_query:
            return
        groups.setdefault(label, [])
        if query not in groups[label]:
            groups[label].append(query)

    def add_filter_variants(source: str) -> None:
        filters = session.filters if isinstance(session.filters, dict) else {}
        for variant in filters.get("query_variants", []):
            if not isinstance(variant, dict):
                continue
            add(source, variant.get("query", ""))

    filters = session.filters if isinstance(session.filters, dict) else {}
    filter_variants = filters.get("query_variants", [])
    if isinstance(filter_variants, list) and filter_variants:
        # Standard search executes the persisted query_variants against each
        # routed source. Merged SearchHit records keep `sources[]` and
        # `query_variants[]`, but not the exact source->variant pairs. Prefer
        # session-level variants grouped by observed source to avoid assigning
        # one merged hit's first query_variant to every source.
        sources_from_summary = [
            source
            for source, count in (session.source_summary or {}).items()
            if count
        ]
        if sources_from_summary:
            for source in sources_from_summary:
                add_filter_variants(source)
        elif any(
            hit.sources or hit.source or hit.backend
            for hit in session.hits
        ):
            seen_sources: list[str] = []
            for hit in session.hits:
                hit_sources = hit.sources or [hit.source or hit.backend]
                for source in hit_sources:
                    if source and source not in seen_sources:
                        seen_sources.append(source)
            for source in seen_sources:
                add_filter_variants(source)
        else:
            add_filter_variants("seed")

    if groups:
        ordered: list[dict] = []
        for source in source_order:
            queries = groups.pop(source, None)
            if queries:
                ordered.append({"source": source, "queries": queries})
        for source, queries in groups.items():
            if queries:
                ordered.append({"source": source, "queries": queries})
        return ordered

    for hit in session.hits:
        hit_queries: list[str] = []
        if hit.query_variant:
            hit_queries.append(hit.query_variant)
        for marker in hit.query_variants:
            if ":" in marker:
                _, marker_query = marker.split(":", 1)
            else:
                marker_query = marker
            if marker_query and marker_query not in hit_queries:
                hit_queries.append(marker_query)
        if hit.sources:
            sources = hit.sources
        elif hit.source or hit.backend:
            sources = [hit.source or hit.backend]
        elif len(session.source_summary or {}) == 1:
            sources = list(session.source_summary.keys())
        else:
            sources = ["seed"]
        for source in sources:
            for query in hit_queries:
                add(source, query)

    if not groups:
        fallback_sources = list(session.source_summary.keys()) if session.source_summary else []
        if fallback_sources:
            for source in fallback_sources:
                add_filter_variants(source)

    if not groups:
        add_filter_variants("seed")

    if not groups:
        for variant in _query_variants_from_session(session):
            add("seed", variant.get("query", ""))

    ordered: list[dict] = []
    for source in source_order:
        queries = groups.pop(source, None)
        if queries:
            ordered.append({"source": source, "queries": queries})
    for source, queries in groups.items():
        if queries:
            ordered.append({"source": source, "queries": queries})
    return ordered


def _build_theme_treemap(papers: list[dict], *, apply_quality_gate: bool = True) -> dict:
    """Build seed-preview topic groups with the same structured-first order as full workflow."""

    keyword_topic = build_keyword_topic_themes(papers)
    if keyword_topic["themes"]:
        keyword_topic["method"] = "seed_keywords_topics_frequency_fallback"
        keyword_topic["note"] = (
            "Seed-preview topic groups derived from repeated keywords/topics already present in the "
            "seed metadata, reusing the same structured-first clustering order as full workflow."
        )
        return keyword_topic

    text_fallback = build_text_themes(papers, apply_quality_gate=apply_quality_gate)
    if not text_fallback["themes"] and papers and not text_fallback.get("status"):
        text_fallback["themes"] = [
            {
                "name": "Paper Set",
                "value": len(papers),
                "paper_ids": [
                    str(paper.get("paper_id") or paper.get("id") or f"seed-{index}")
                    for index, paper in enumerate(papers, 1)
                ],
            }
        ]
    text_fallback["method"] = "seed_text_frequency_fallback"
    text_fallback["note"] = (
        "Seed-preview topic groups derived from repeated title and abstract terms because "
        "structured keywords/topics were unavailable in the seed metadata."
    )
    return text_fallback


def _load_theme_postprocess_result(materialized_dir: Path) -> dict | None:
    result_path = materialized_dir / THEME_POSTPROCESS_RESULT_FILENAME
    if not result_path.exists():
        return None
    data = json.loads(result_path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def _apply_theme_postprocess(
    raw_theme_treemap: dict,
    papers: list[dict],
    *,
    report_mode: str,
    materialized_dir: Path | None = None,
) -> tuple[dict, dict, dict]:
    request_payload, trace = build_theme_postprocess_request(
        raw_theme_treemap,
        papers,
        report_mode=report_mode,
    )
    result_payload = _load_theme_postprocess_result(materialized_dir) if materialized_dir else None
    if result_payload is None:
        return raw_theme_treemap, trace, request_payload
    refined, applied_trace = apply_theme_postprocess_result(
        raw_theme_treemap,
        result_payload,
        model_label="host-agent",
    )
    return refined, applied_trace, request_payload


def _has_effective_theme_signal(theme_treemap: dict | None) -> bool:
    if not isinstance(theme_treemap, dict):
        return False
    themes = theme_treemap.get("themes") or []
    for theme in themes:
        if not isinstance(theme, dict):
            continue
        try:
            value = int(theme.get("value") or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0 and theme.get("name"):
            return True
    return False


def _reconcile_quality_profile_with_chart_signals(
    quality_profile: dict,
    chart_data: dict,
) -> dict:
    reconciled = dict(quality_profile or {})
    if (
        reconciled.get("topic_analysis_mode") == "disabled"
        and _has_effective_theme_signal(
            (chart_data or {}).get("raw_theme_treemap")
            or (chart_data or {}).get("theme_treemap")
        )
    ):
        reconciled["topic_analysis_mode"] = "limited"
    return reconciled


GENERIC_RECOVERED_LABELS = {
    "",
    "recovered local files",
    "recovered local file",
    "local files",
    "local file recovery",
    "recovered report",
    "recovered reports",
    "recovered paper set",
    "recovered papers",
    "paper set",
    "paper collection",
    "cnki 下载结果集合",
    "本地文件结果集合",
    "本地文件恢复",
    "历史报告恢复",
    "恢复报告",
    "恢复文献集",
    "文献集合",
}


GENERIC_THEME_LABELS = {
    "paper set",
    "paper collection",
    "document set",
    "documents",
    "unknown",
    "uncategorized",
    "miscellaneous",
    "other",
    "文献集合",
    "文献集",
    "其他",
    "未分类",
}


def _normalize_display_text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _is_generic_recovered_label(label: str) -> bool:
    normalized = _normalize_display_text(label).strip("[]【】（）()：:").lower()
    return normalized in GENERIC_RECOVERED_LABELS


def _recovery_kind_from_session(session: SearchSession) -> str:
    origin = session.origin if isinstance(session.origin, dict) else {}
    filters = session.filters if isinstance(session.filters, dict) else {}
    origin_kind = origin.get("kind")
    recovered_from = filters.get("recovered_from")
    if origin_kind == "download_sidecar" or recovered_from == "download_sidecar":
        return "A"
    if recovered_from == "legacy_report_json":
        return "B"
    if recovered_from == "local_files":
        return "C"
    return ""


def _recovery_title_prefix(recovery_kind: str) -> str:
    return {
        "A": "[下载记录恢复]：",
        "B": "[历史报告恢复]：",
        "C": "[本地文件恢复]：",
    }.get(recovery_kind, "")


def _theme_name_is_generic(name: str) -> bool:
    normalized = _normalize_display_text(name).lower()
    return not normalized or normalized in GENERIC_THEME_LABELS


def _semantic_title_from_theme_treemap(theme_treemap: dict | None) -> str:
    if not isinstance(theme_treemap, dict):
        return ""
    ranked: list[tuple[int, int, str]] = []
    for index, theme in enumerate(theme_treemap.get("themes") or []):
        if not isinstance(theme, dict):
            continue
        name = _normalize_display_text(theme.get("name"))
        if _theme_name_is_generic(name):
            continue
        try:
            value = int(theme.get("value") or 0)
        except (TypeError, ValueError):
            value = 0
        if value <= 0:
            continue
        ranked.append((value, -index, name))
    ranked.sort(reverse=True)
    names: list[str] = []
    for _, _, name in ranked:
        if name not in names:
            names.append(name)
        if len(names) >= 2:
            break
    return " / ".join(names)


def _semantic_title_from_papers(papers: list[dict]) -> str:
    titles = [
        _normalize_display_text(paper.get("title"))
        for paper in papers
        if _normalize_display_text(paper.get("title"))
    ]
    if not titles:
        return ""
    if len(titles) == 1:
        return titles[0]
    # Multi-paper title-only recovery should not pretend to know more than the
    # available metadata. Use the first non-empty title only when no theme
    # signal can be derived at all.
    return titles[0]


def _resolve_report_display_queries(
    session: SearchSession,
    *,
    explicit_display_query: str = "",
    chart_data: dict | None = None,
    papers: list[dict] | None = None,
) -> dict:
    """Resolve report-visible title without overwriting the true original query."""

    original_query = _normalize_display_text(session.query)
    session_display_query = _normalize_display_text(session.display_query)
    recovered_label = _normalize_display_text(session.recovered_label)
    recovery_kind = _recovery_kind_from_session(session)
    resolved_display_query = ""
    source = ""

    candidates = [
        ("explicit_display_query", explicit_display_query),
        ("session_display_query", session_display_query),
        ("original_query", original_query),
    ]
    for candidate_source, candidate in candidates:
        text = _normalize_display_text(candidate)
        if text:
            resolved_display_query = text
            source = candidate_source
            break

    if (
        not resolved_display_query
        and recovered_label
        and (not recovery_kind or not _is_generic_recovered_label(recovered_label))
    ):
        resolved_display_query = recovered_label
        source = "recovered_label"

    if not resolved_display_query:
        theme_title = _semantic_title_from_theme_treemap(
            (chart_data or {}).get("theme_treemap")
            or (chart_data or {}).get("raw_theme_treemap")
        )
        if theme_title:
            resolved_display_query = theme_title
            source = "theme_treemap"

    if not resolved_display_query:
        paper_title = _semantic_title_from_papers(papers or [])
        if paper_title:
            resolved_display_query = paper_title
            source = "paper_titles"

    if not resolved_display_query and recovered_label:
        resolved_display_query = recovered_label
        source = "generic_recovered_label"

    if not resolved_display_query:
        resolved_display_query = "文献集合"
        source = "fallback"

    prefix = _recovery_title_prefix(recovery_kind)
    display_title = f"{prefix}{resolved_display_query}" if prefix else resolved_display_query
    return {
        "display_query": resolved_display_query,
        "display_title": display_title,
        "display_query_source": source,
        "recovery_kind": recovery_kind,
    }


def _build_report_summary(display_query: str, paper_count: int, language: str) -> str:
    display_query = _normalize_display_text(display_query)
    if (language or "").lower().startswith("zh"):
        if display_query:
            return f"当前文献集主要围绕 {display_query}，包含 {paper_count} 篇文献。"
        return f"当前文献集包含 {paper_count} 篇文献。"
    if display_query:
        return f"The current paper set mainly focuses on {display_query}, covering {paper_count} papers."
    return f"The current paper set contains {paper_count} papers."


def _build_chart_data(
    papers: list[dict],
    source_summary: dict,
    *,
    materialized_dir: Path | None = None,
    report_mode: str = "seed_preview",
) -> dict:
    years: dict[int, dict[str, int]] = {}
    rcs_counts = [0] * 11
    for paper in papers:
        year = paper.get("year")
        valid_rcs = _rcs_value_if_valid(paper)
        if year:
            years.setdefault(int(year), {"year": int(year), "total": 0, "highly_relevant": 0})
            years[int(year)]["total"] += 1
            if valid_rcs is not None and valid_rcs >= 7:
                years[int(year)]["highly_relevant"] += 1
        if valid_rcs is not None:
            rcs_counts[valid_rcs] += 1
    total = len(papers)
    valid_rcs_values = [
        rcs
        for paper in papers
        for rcs in [_rcs_value_if_valid(paper)]
        if rcs is not None
    ]
    valid_total = len(valid_rcs_values)
    highly = sum(1 for rcs in valid_rcs_values if rcs >= 7)
    closely = sum(1 for rcs in valid_rcs_values if rcs in (5, 6))
    coverage = 0.0 if total == 0 else min(0.98, max(0.5, total / (total + max(1, closely))))
    ci_band = 0.15 if total < 50 else 0.08
    estimated_total = highly / coverage if coverage > 0 else 0.0
    discovery_points = [
        {"papers_screened": 0, "found": 0},
        {"papers_screened": total, "found": highly},
    ]
    summary = (
        f"Estimated to have found about {highly} relevant papers, "
        f"approximately {coverage*100:.0f}% of the relevant set "
        f"(95% CI: {max(0.0, coverage - ci_band)*100:.0f}-{min(1.0, coverage + ci_band)*100:.0f}%)."
    )
    ungated_theme_treemap = _build_theme_treemap(papers, apply_quality_gate=False)
    gated_theme_treemap = _build_theme_treemap(papers, apply_quality_gate=True)
    raw_theme_treemap = ungated_theme_treemap if not gated_theme_treemap.get("themes") else gated_theme_treemap
    theme_treemap, theme_postprocess, theme_postprocess_request = _apply_theme_postprocess(
        gated_theme_treemap,
        papers,
        report_mode=report_mode,
        materialized_dir=materialized_dir,
    )
    return {
        "year_counts": {str(year): data["total"] for year, data in years.items()},
        "source_summary": source_summary,
        "total_papers": total,
        "publication_year": {
            "bins": [years[year] for year in sorted(years)],
            "year_min": min(years) if years else None,
            "year_max": max(years) if years else None,
        },
        "relevance_score": {
            "bins": (
                [{"rcs": i, "count": rcs_counts[i]} for i in range(11)]
                if valid_total
                else []
            ),
            "mean": round(sum(i * rcs_counts[i] for i in range(11)) / valid_total, 2) if valid_total else None,
            "ci_low": None,
            "ci_high": None,
            "n": valid_total,
        },
        "discovery_curve": {
            "points": discovery_points,
            "tau": 80.0,
            "coverage_estimate": round(coverage, 3),
            "ci_low": round(max(0.0, coverage - ci_band), 3),
            "ci_high": round(min(1.0, coverage + ci_band), 3),
            "estimated_total_relevant": round(estimated_total, 1),
            "summary": summary,
        },
        "citation_network": {
            "nodes": [
                {
                    "id": p["paper_id"],
                    "year": p.get("year"),
                    "citation_count": p.get("citation_count") or 0,
                    "rcs": p.get("rcs") or 0,
                    "rcs_valid": _rcs_value_if_valid(p) is not None,
                    "rcs_source": p.get("rcs_source") or "",
                    "title": p.get("title") or "",
                    "authors_short": p.get("authors_short") or "",
                    "venue": p.get("venue") or "",
                    "doi_url": p.get("doi_url"),
                    "is_seed": True,
                }
                for p in papers[:150]
                if p.get("year")
            ],
            "edges": [],
        },
        "raw_theme_treemap": raw_theme_treemap,
        "theme_treemap": theme_treemap,
        "theme_postprocess": theme_postprocess,
        "theme_postprocess_request": theme_postprocess_request,
    }


def _report_label_mode(quality_profile: dict) -> str:
    title_mode = quality_profile.get("title_mode")
    if title_mode == "search":
        return "检索结果"
    if title_mode == "summary":
        return "结果总结"
    return "恢复总结"


PRISMA_STEP_KEYS: tuple[str, ...] = (
    "1_database_information",
    "2_multi_database_searching",
    "3_study_registries",
    "4_online_resources_browsing",
    "5_citation_searching",
    "6_contacts",
    "7_other_methods",
    "8_full_search_strategies",
    "9_limits_and_restrictions",
    "10_search_filters",
    "11_prior_work",
    "12_updates",
    "13_dates_of_searches",
    "14_total_records",
    "15_deduplication",
    "16_record_management",
)


def _seed_step_not_performed(note: str) -> dict:
    return {"performed": False, "note": note}


def _build_seed_prisma_log(
    session: SearchSession,
    papers: list[dict],
    metadata: dict,
    *,
    report_mode: str = "seed_preview",
) -> dict:
    """Build a lightweight, renderer-compatible PRISMA-S disclosure for seed previews."""

    sources = [source for source, count in sorted((session.source_summary or {}).items()) if count]
    if not sources:
        sources = sorted(
            {
                source
                for paper in papers
                for source in (paper.get("sources") or [])
                if source and source != "seed"
            }
        )
    if not sources:
        sources = ["vpnsci_seed"]

    query_variants = _query_variants_from_session(session)
    generated_at = metadata.get("generated_at") or datetime.now(timezone.utc).isoformat()

    log = {
        "1_database_information": {
            "databases": sources,
            "primary": sources[0] if sources else "vpnsci_seed",
            "note": "Seed-preview disclosure generated from an existing vpnsci-sustech Search Session.",
        },
        "2_multi_database_searching": {
            "performed": len(sources) > 1,
            "databases": sources,
            "note": "True when the seed Search Session contains records from multiple metadata sources.",
        },
        "3_study_registries": {
            "queried": False,
            "note": f"Not performed in {report_mode} mode.",
        },
        "4_online_resources_browsing": _seed_step_not_performed(f"Not performed in {report_mode} mode."),
        "5_citation_searching": _seed_step_not_performed(f"Citation chasing is part of full paper-search-pro, not {report_mode}."),
        "6_contacts": _seed_step_not_performed(f"Author/contact search is not performed in {report_mode} mode."),
        "7_other_methods": {
            "performed": True,
            "note": "Existing vpnsci-sustech Search Session reused as seed evidence for quick HTML reporting.",
        },
        "8_full_search_strategies": {
            "performed": True,
            "user_query": metadata.get("seed_session_query") or session.query or metadata.get("display_query") or metadata.get("query"),
            "seed_session_query": session.query,
            "query_variants": query_variants,
            "note": "Records the available query variants from the seed Search Session; not a full upstream query plan.",
        },
        "9_limits_and_restrictions": {
            "performed": True,
            "limits": [
                f"{report_mode} mode",
                "existing Search Session only",
                "no full source expansion",
                "no full-workflow SubAgent relevance grading",
            ],
        },
        "10_search_filters": {
            "performed": bool(session.filters),
            "filters": session.filters or {},
        },
        "11_prior_work": _seed_step_not_performed(f"Prior systematic review search is not performed in {report_mode} mode."),
        "12_updates": _seed_step_not_performed(f"Search update tracking is not performed in {report_mode} mode."),
        "13_dates_of_searches": {
            "performed": True,
            "generated_at": generated_at,
            "seed_created_at": session.created_at,
        },
        "14_total_records": {
            "performed": True,
            "records": len(papers),
            "source_summary": session.source_summary or {},
        },
        "15_deduplication": {
            "performed": True,
            "deduped_records": len(papers),
            "note": "Count reflects records already persisted in the vpnsci-sustech Search Session.",
        },
        "16_record_management": {
            "performed": True,
            "search_id": session.session_id,
            "report_mode": report_mode,
            "outputs": ["metadata.json", "paper_list.json", "chart_data.json", "prisma_log.json", "report_data.json", "report.html"],
        },
        "_meta": {
            "mode": report_mode,
            "is_full_prisma_s": False,
            "note": "Lightweight disclosure only; full PRISMA-S requires generate_search_report(..., mode='full') and the upstream paper-search-pro workflow.",
        },
    }
    missing = [key for key in PRISMA_STEP_KEYS if key not in log]
    if missing:
        raise RuntimeError(f"Seed PRISMA disclosure missing steps: {', '.join(missing)}")
    return log


def _write_materialized_data(
    session: SearchSession,
    output_dir: Path,
    *,
    display_query: str = "",
    language: str = "",
    report_mode: str = "seed_preview",
    rcs_classification_result: object | None = None,
    rcs_execution_mode: str = "none",
) -> Path:
    data_dir = output_dir / "materialized"
    data_dir.mkdir(parents=True, exist_ok=True)
    original_query = session.query or ""
    recovered_label = session.recovered_label or ""
    pre_resolved_display_query = display_query or session.display_query or original_query
    papers = [_paper_from_hit(hit, i, pre_resolved_display_query) for i, hit in enumerate(session.hits, 1)]
    if rcs_classification_result is not None:
        papers = _apply_rcs_classification_result(papers, rcs_classification_result)
    chart_data = _build_chart_data(
        papers,
        session.source_summary,
        materialized_dir=data_dir,
        report_mode=report_mode,
    )
    display_resolution = _resolve_report_display_queries(
        session,
        explicit_display_query=display_query,
        chart_data=chart_data,
        papers=papers,
    )
    resolved_display_query = display_resolution["display_query"]
    display_query_field = resolved_display_query
    if (
        display_resolution["display_query_source"] in {"recovered_label", "generic_recovered_label"}
        and not display_query
        and not session.display_query
    ):
        display_query_field = ""
    report_query = display_resolution["display_title"]
    report_language = language or _detect_language(report_query)
    report_summary = _build_report_summary(resolved_display_query, len(papers), report_language)
    rcs_coverage = _rcs_coverage_metadata(papers, rcs_execution_mode=rcs_execution_mode)
    valid_rcs_values = [
        rcs
        for paper in papers
        for rcs in [_rcs_value_if_valid(paper)]
        if rcs is not None
    ]
    highly = sum(1 for rcs in valid_rcs_values if rcs >= 7)
    closely = sum(1 for rcs in valid_rcs_values if rcs in (5, 6))
    discovery_curve = chart_data["discovery_curve"]
    actual_query_variants = _query_variants_from_session(session)
    actual_query_groups = _actual_query_groups_from_session(session, display_query=resolved_display_query or original_query)
    year_count = sum(1 for paper in papers if paper.get("year"))
    citation_count = sum(1 for paper in papers if (paper.get("citation_count") or 0) > 0)
    topic_signal_count = sum(1 for paper in papers if paper.get("abstract") or paper.get("keywords"))
    origin = session.origin if isinstance(session.origin, dict) else {}
    quality_profile = infer_quality_profile(
        origin_kind=origin.get("kind", ""),
        recovery_capability=str(origin.get("report_recovery_capability") or ""),
        actual_queries=actual_query_groups,
        total_hits=len(papers),
        field_presence={
            "actual_queries": len(actual_query_groups),
            "year": year_count,
            "citation_count": citation_count,
            "abstract_or_keywords": topic_signal_count,
        },
        original_query=original_query,
        display_query=display_query_field,
        recovered_label=recovered_label,
    )
    quality_profile = _reconcile_quality_profile_with_chart_signals(quality_profile, chart_data)
    missing_fields, insufficient_fields = split_missing_and_insufficient_fields(
        total_hits=len(papers),
        field_presence={
            "actual_queries": len(actual_query_groups),
            "year": year_count,
            "citation_count": citation_count,
        },
    )
    if quality_profile["discovery_curve_mode"] == "disabled":
        discovery_curve["mode"] = "disabled"
        recovery_capability = str(origin.get("report_recovery_capability") or "")
        if recovery_capability and recovery_capability != "standard":
            discovery_curve["status"] = "degraded_recovery"
            discovery_curve["reason"] = "恢复材料能力不足，当前不输出覆盖率/饱和度结论。"
        else:
            discovery_curve["status"] = "missing_data" if "actual_queries" in missing_fields else "insufficient_data"
            discovery_curve["reason"] = (
                "缺少可解释的执行轨迹，当前不输出覆盖率/饱和度结论。"
                if "actual_queries" in missing_fields
                else "样本量过小，当前不输出覆盖率/饱和度结论。"
            )
        discovery_curve["coverage_estimate"] = None
        discovery_curve["ci_low"] = None
        discovery_curve["ci_high"] = None
        discovery_curve["estimated_total_relevant"] = None
        discovery_curve["summary"] = ""
    else:
        discovery_curve["mode"] = "enabled"
        discovery_curve["status"] = "ok"
    chart_data["citation_analysis"] = {
        "mode": quality_profile["citation_analysis_mode"],
        "status": (
            "ok"
            if quality_profile["citation_analysis_mode"] == "enabled"
            else "missing_data" if citation_count == 0 and year_count == 0 else "insufficient_data"
        ),
        "reason": (
            ""
            if quality_profile["citation_analysis_mode"] == "enabled"
            else "缺少足够 citation/year 元数据，当前不输出 citation × year 分析。"
        ),
    }
    metadata = {
        "query": report_query,
        "original_query": original_query,
        "language": report_language,
        "seed_source": _seed_source_label(session),
        "cnki_fields": _cnki_field_status(session),
        "user_query": report_query,
        "display_query": display_query_field,
        "display_title": report_query,
        "display_query_source": display_resolution["display_query_source"],
        "recovered_label": recovered_label,
        "summary": report_summary,
        "seed_session_query": original_query,
        "actual_query_variants": actual_query_variants,
        "query_display": {
            "user_query": report_query,
            "primary": report_query,
            "expanded": actual_query_variants,
            "actual_queries": actual_query_groups,
        },
        "quality_profile": quality_profile,
        "recovery_kind": display_resolution["recovery_kind"],
        "report_recovery_capability": str(origin.get("report_recovery_capability") or ""),
        "report_label_mode": _report_label_mode(quality_profile),
        "missing_fields": missing_fields,
        "insufficient_analysis_fields": insufficient_fields,
        "search_id": session.session_id,
        "seed_session_id": session.session_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_papers": len(papers),
        "papers_evaluated": len(papers),
        "papers_in_kg": len(papers),
        "highly_relevant_count": highly,
        "closely_related_count": closely,
        **rcs_coverage,
        "coverage_estimate": discovery_curve["coverage_estimate"],
        "coverage_ci": [discovery_curve["ci_low"], discovery_curve["ci_high"]],
        "coverage_label": "seed preview estimate" if discovery_curve["coverage_estimate"] is not None else "",
        "source_summary": session.source_summary,
        "mode": "vpnsci-seed-report",
        "report_mode": report_mode,
        "tier": "standard",
    }
    prisma_log = _build_seed_prisma_log(session, papers, metadata, report_mode=report_mode)
    report_data = {
        "metadata": metadata,
        "chart_data": chart_data,
        "paper_list": papers,
        "prisma_log": prisma_log,
        "summary": report_summary,
    }
    theme_postprocess_request = chart_data.get("theme_postprocess_request")
    (data_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "paper_list.json").write_text(json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "chart_data.json").write_text(json.dumps(chart_data, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "prisma_log.json").write_text(json.dumps(prisma_log, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "report_data.json").write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
    if theme_postprocess_request:
        (data_dir / THEME_POSTPROCESS_REQUEST_FILENAME).write_text(
            json.dumps(theme_postprocess_request, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if report_mode == "seed_classified":
        rcs_request = _build_rcs_classification_request(
            papers,
            query=report_query,
            language=report_language,
            report_mode=report_mode,
        )
        (data_dir / RCS_CLASSIFICATION_REQUEST_FILENAME).write_text(
            json.dumps(rcs_request, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return data_dir


def prepare_report(
    seed_json: Path,
    output_dir: Path,
    *,
    display_query: str = "",
    language: str = "",
    report_mode: str = "seed_preview",
    rcs_classification_result: object | None = None,
    rcs_execution_mode: str = "none",
) -> dict:
    """Prepare materialized data and expose theme-postprocess artifact paths."""

    session = _load_seed(seed_json)
    output_dir.mkdir(parents=True, exist_ok=True)
    materialized_dir = _write_materialized_data(
        session,
        output_dir,
        display_query=display_query,
        language=language,
        report_mode=report_mode,
        rcs_classification_result=rcs_classification_result,
        rcs_execution_mode=rcs_execution_mode,
    )
    selected_language = language or _detect_language(display_query or session.query)
    request_path = materialized_dir / THEME_POSTPROCESS_REQUEST_FILENAME
    result_path = materialized_dir / THEME_POSTPROCESS_RESULT_FILENAME
    rcs_request_path = materialized_dir / RCS_CLASSIFICATION_REQUEST_FILENAME
    rcs_result_path = materialized_dir / RCS_CLASSIFICATION_RESULT_FILENAME
    return {
        "session_id": session.session_id,
        "report_path": str(output_dir / "report.html"),
        "materialized_dir": str(materialized_dir),
        "theme_postprocess_request_path": str(request_path),
        "theme_postprocess_result_path": str(result_path),
        "theme_postprocess_pending": request_path.exists() and not result_path.exists(),
        "rcs_classification_request_path": str(rcs_request_path),
        "rcs_classification_result_path": str(rcs_result_path),
        "rcs_classification_pending": rcs_request_path.exists() and not rcs_result_path.exists(),
        "user_query": display_query or session.query,
        "language": selected_language,
    }


def render_report(
    seed_json: Path,
    output_dir: Path,
    *,
    display_query: str = "",
    language: str = "",
    open_report: bool = False,
) -> Path:
    config = Config.load()
    tool_root = Path(config.paper_search_pro_root)
    if not tool_root.exists():
        raise FileNotFoundError(f"paper-search-pro local runtime not found: {tool_root}")
    prepared = prepare_report(
        seed_json,
        output_dir,
        display_query=display_query,
        language=language,
    )
    session = _load_seed(seed_json)
    materialized_dir = Path(prepared["materialized_dir"])
    sys.path.insert(0, str(tool_root))

    selected_language = str(prepared["language"] or language or _detect_language(display_query or session.query))
    report_path = output_dir / "report.html"
    render_html_webartifacts(
        materialized_data_dir=materialized_dir,
        output_path=report_path,
        user_query=display_query or session.query,
        language=selected_language,
    )
    if open_report:
        webbrowser.open(report_path.resolve().as_uri())
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render vpnsci seed session with paper-search-pro assets")
    parser.add_argument("--seed", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--display-query", default="")
    parser.add_argument("--language", choices=["en", "zh"], default="")
    parser.add_argument("--open-report", action="store_true")
    args = parser.parse_args()
    report = render_report(
        args.seed,
        args.output_dir,
        display_query=args.display_query,
        language=args.language,
        open_report=args.open_report,
    )
    print(f"report.html: {report}")


if __name__ == "__main__":
    main()
