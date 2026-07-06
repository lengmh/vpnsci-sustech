"""Materialize a classified KG into the JSON bundle consumed by renderers.

Produces a single `report_data.json` (consumed by html_renderer_webartifacts /
md_report) plus four sibling JSON files for tools that
expect the per-section schema:

- chart_data.json    : 5 chart datasets (year hist / RCS dist / discovery /
                       network / themes)
- paper_list.json    : per-paper render data (doi_url, authors_short, rcs, tldr,
                       ...)
- metadata.json      : query, tier, wall_clock, papers_evaluated,
                       coverage_estimate, ...
- prisma_log.json    : PRISMA-S 16-item checklist (built by prisma_s_logger)

v2.0 refactor: SearchState removed. `materialize` accepts the classified KG +
summary text + user_query + tier directly. Optional execution metadata
(wall_clock_seconds, discovery_curve_snapshots, search_id) lets the main agent
fill PRISMA-S item 13 / 16 when it knows the values.
"""

import json
import math
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .discovery_curve import build_discovery_curve_payload
from .theme_clustering import build_keyword_topic_themes, build_text_themes
from .theme_postprocess import (
    THEME_POSTPROCESS_REQUEST_FILENAME,
    THEME_POSTPROCESS_RESULT_FILENAME,
    apply_theme_postprocess_result,
    build_theme_postprocess_request,
)
from .types import UnifiedPaperEntity

INVALID_RCS_FLAGS = {"parse_failed_uncertain"}
VALID_RCS_EXECUTION_MODES = {"none", "subagent_parallel", "main_agent_serial"}


def _dump(path: Path, obj: Any) -> Path:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def _resolve_wall_clock(
    *,
    wall_clock_seconds: Optional[float],
    started_at: Optional[str],
    kg_source_path: Optional[Path],
) -> Optional[float]:
    """P0-7 fix: produce a non-zero wall_clock when caller didn't pass it.

    Priority:
      1. Explicit ``wall_clock_seconds`` (preserved as-is, including 0.0 if
         truly meant — see clamp note below).
      2. ``started_at`` ISO timestamp → ``now - started_at``.
      3. ``kg_source_path`` mtime → ``now - kg.mtime`` (loosest fallback).

    Returns None only when all paths fail, in which case _build_metadata writes
    0.0 (the prior behavior). Negative deltas (clock skew / stale files) are
    clamped to 0.
    """
    if wall_clock_seconds is not None:
        return wall_clock_seconds
    if started_at:
        try:
            # Accept both naive and TZ-aware ISO strings; strip a trailing 'Z'.
            iso = started_at.rstrip("Z") if started_at.endswith("Z") else started_at
            t0 = datetime.fromisoformat(iso)
            delta = (datetime.now() - t0).total_seconds()
            return max(0.0, delta)
        except (ValueError, TypeError):
            pass
    if kg_source_path is not None:
        try:
            mtime = Path(kg_source_path).stat().st_mtime
            return max(0.0, time.time() - mtime)
        except OSError:
            pass
    return None


def materialize(
    kg: Dict[str, UnifiedPaperEntity],
    output_dir: Path,
    *,
    user_query: str = "",
    tier: str = "standard",
    search_id: str = "",
    summary: str = "",
    query_plan: Optional[List[Dict]] = None,
    discovery_curve_snapshots: Optional[List[Dict]] = None,
    wall_clock_seconds: Optional[float] = None,
    stop_reason: Optional[str] = None,
    started_at: Optional[str] = None,
    kg_source_path: Optional[Path] = None,
    rcs_execution_mode: str = "subagent_parallel",
) -> Dict[str, Path]:
    """Write chart_data / paper_list / metadata / prisma_log + report_data.

    Args:
        kg: classified knowledge graph (canonical_key -> paper).
        output_dir: directory where the JSON files will land.
        user_query: original natural-language query.
        tier: tier name (quick / standard / deep / audit).
        search_id: optional search ID for PRISMA-S item 16.
        summary: executive summary text (markdown, written by main agent).
        discovery_curve_snapshots: optional list of snapshot dicts produced by
            discovery_curve.make_snapshot — feeds the saturation curve panel.
        wall_clock_seconds: optional wall-clock elapsed time. Preferred direct path.
        stop_reason: optional final stop reason string.
        started_at: optional ISO timestamp marking when the main agent's STEP 1
            began. When provided and `wall_clock_seconds` is None, the elapsed
            time is computed from (now - started_at). P0-7 fix.
        kg_source_path: optional path to the kg.json that fed this run; used as
            a graceful fallback for wall_clock when neither
            `wall_clock_seconds` nor `started_at` is provided (uses
            now - kg.json mtime). P0-7 graceful fallback.
        rcs_execution_mode: how formal RCS classification was executed. The
            normal full workflow uses ``subagent_parallel``; explicit serial
            fallback should pass ``main_agent_serial`` so the report can
            disclose it.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    discovery_curve_snapshots = discovery_curve_snapshots or []
    query_plan = query_plan or []

    # P0-7 fix: derive wall_clock when caller didn't pass it directly.
    wall_clock_seconds = _resolve_wall_clock(
        wall_clock_seconds=wall_clock_seconds,
        started_at=started_at,
        kg_source_path=kg_source_path,
    )

    classified = [p for p in kg.values() if p.rcs is not None]
    if not classified:
        # Allow callers to materialise an unclassified KG (degraded but useful).
        classified = list(kg.values())

    chart_data = {
        "publication_year": _build_year_histogram(classified),
        "relevance_score": _build_rcs_distribution(classified),
        "discovery_curve": _build_discovery_curve(discovery_curve_snapshots, classified),
        # max_nodes 50 → 150 (2026-05-23). React CitationScatter handles 150+
        # log-scale dots comfortably; previous cap was a payload-size guess
        # from when the hydrated bundle was capped at 1.5 MB. With 5 MB now
        # acceptable, the broader citation-graph view is worth +25 KB.
        "citation_network": _build_citation_network(classified, max_nodes=150),
        **_build_theme_chart_payload(classified, output_dir=output_dir),
    }
    paper_list = [_render_paper(p) for p in _sorted_for_display(classified)]
    metadata = _build_metadata(
        kg=kg,
        classified=classified,
        discovery_curve=chart_data["discovery_curve"],
        user_query=user_query,
        tier=tier,
        search_id=search_id,
        wall_clock_seconds=wall_clock_seconds,
        stop_reason=stop_reason,
        query_plan=query_plan,
        rcs_execution_mode=rcs_execution_mode,
    )

    from .prisma_s_logger import build_prisma_s_log  # lazy; sibling module
    prisma_log = build_prisma_s_log(
        kg,
        user_query=user_query,
        tier=tier,
        search_id=search_id,
        query_plan=query_plan,
        discovery_curve_snapshots=discovery_curve_snapshots,
        wall_clock_seconds=wall_clock_seconds,
    )

    report_data = {
        "metadata": metadata,
        "chart_data": chart_data,
        "paper_list": paper_list,
        "prisma_log": prisma_log,
        "summary": summary or "",
    }

    return {
        "chart_data": _dump(output_dir / "chart_data.json", chart_data),
        "paper_list": _dump(output_dir / "paper_list.json", paper_list),
        "metadata": _dump(output_dir / "metadata.json", metadata),
        "prisma_log": _dump(output_dir / "prisma_log.json", prisma_log),
        "report_data": _dump(output_dir / "report_data.json", report_data),
    }


# ---------- Chart builders ----------

def _build_year_histogram(papers: List[UnifiedPaperEntity]) -> Dict[str, Any]:
    """Per-year bar chart with highly_relevant overlay. Empty years are omitted."""
    by_year_total: Counter = Counter()
    by_year_highly: Counter = Counter()
    for p in papers:
        if not p.year:
            continue
        by_year_total[p.year] += 1
        valid_rcs = _rcs_value_if_valid(p)
        if valid_rcs is not None and valid_rcs >= 7:
            by_year_highly[p.year] += 1
    if not by_year_total:
        return {"bins": [], "year_min": None, "year_max": None}
    year_min = min(by_year_total)
    year_max = max(by_year_total)
    bins = [
        {
            "year": y,
            "total": by_year_total.get(y, 0),
            "highly_relevant": by_year_highly.get(y, 0),
        }
        for y in range(year_min, year_max + 1)
    ]
    return {"bins": bins, "year_min": year_min, "year_max": year_max}


def _build_rcs_distribution(papers: List[UnifiedPaperEntity]) -> Dict[str, Any]:
    """Histogram of valid formal RCS 0-10 with mean and 95% CI."""
    scored = [
        rcs
        for p in papers
        for rcs in [_rcs_value_if_valid(p)]
        if rcs is not None
    ]
    counts = [0] * 11
    for rcs in scored:
        counts[rcs] += 1
    n = sum(counts)
    if n == 0:
        return {"bins": [], "mean": None, "ci_low": None, "ci_high": None, "n": 0}
    weighted = sum(i * counts[i] for i in range(11))
    mean = weighted / n
    # 95% CI on the mean assuming sample standard deviation; falls back to 0 when n<=1.
    if n > 1:
        var = sum(counts[i] * (i - mean) ** 2 for i in range(11)) / (n - 1)
        stderr = math.sqrt(var) / math.sqrt(n)
    else:
        stderr = 0.0
    ci_low = max(0.0, mean - 1.96 * stderr)
    ci_high = min(10.0, mean + 1.96 * stderr)
    return {
        "bins": [{"rcs": i, "count": counts[i]} for i in range(11)],
        "mean": round(mean, 2),
        "ci_low": round(ci_low, 2),
        "ci_high": round(ci_high, 2),
        "n": n,
    }


def _build_discovery_curve(
    snapshots: List[Dict], papers: List[UnifiedPaperEntity]
) -> Dict[str, Any]:
    """Cumulative discovery vs evaluated, using strict staged evidence only."""

    return build_discovery_curve_payload(snapshots, scope="full_workflow")


def _build_citation_network(
    papers: List[UnifiedPaperEntity], max_nodes: int = 50
) -> Dict[str, Any]:
    """Force-directed graph nodes (top relevance) + edges derived from discovery_path."""
    sorted_papers = sorted(
        papers,
        key=lambda p: (-(_rcs_value_if_valid(p) or 0), -(p.citation_count or 0)),
    )[:max_nodes]
    id_to_node: Dict[str, Dict[str, Any]] = {}
    for p in sorted_papers:
        node_id = p.paper_id
        id_to_node[node_id] = {
            "id": node_id,
            "title": p.title or "(untitled)",
            "authors_short": _authors_short(p),
            "year": p.year,
            "venue": p.venue,
            "rcs": p.rcs,
            "rcs_valid": _rcs_value_if_valid(p) is not None,
            "rcs_source": _rcs_source_for_paper(p),
            "citation_count": p.citation_count or 0,
            "doi_url": p.doi_url or (f"https://doi.org/{p.doi}" if p.doi else None),
            "is_seed": (p.discovery_path or "").startswith("query:"),
        }

    edges: List[Dict[str, str]] = []
    seen_pairs: set = set()
    for p in sorted_papers:
        dp = p.discovery_path or ""
        # discovery_path examples: "ref of W12345", "cites W23456", "query: prospect theory"
        if dp.startswith("ref of ") or dp.startswith("cites "):
            target = dp.split(" ", 2)[-1].strip()
            # Only connect if target exists in graph
            if target in id_to_node and target != p.paper_id:
                key = tuple(sorted([p.paper_id, target]))
                if key not in seen_pairs:
                    edges.append({"source": p.paper_id, "target": target})
                    seen_pairs.add(key)

    return {
        "nodes": list(id_to_node.values()),
        "edges": edges,
        "node_count": len(id_to_node),
        "edge_count": len(edges),
    }


def _build_themes(papers: List[UnifiedPaperEntity], *, apply_quality_gate: bool = True) -> Dict[str, Any]:
    """Frequency-based clustering of keywords/topics into theme buckets.

    No LLM call here — that keeps materialization deterministic and cheap. The
    write_report tool can optionally enrich this later via theme_extraction.
    """
    data = build_keyword_topic_themes(
        [
            {
                "paper_id": p.paper_id,
                "keywords": p.keywords or [],
                "topics": p.topics or [],
            }
            for p in papers
        ]
    )
    if not data["themes"]:
        text_fallback = build_text_themes(
            [
                {
                    "paper_id": p.paper_id,
                    "title": p.title,
                    "abstract": p.abstract,
                }
                for p in papers
            ],
            apply_quality_gate=apply_quality_gate,
        )
        if not text_fallback["themes"] and papers and not text_fallback.get("status"):
            text_fallback["themes"] = [
                {
                    "name": "Paper Set",
                    "value": len(papers),
                    "paper_ids": [p.paper_id for p in papers],
                }
            ]
        text_fallback["method"] = "text_frequency_fallback"
        text_fallback["note"] = (
            "Theme groups derived from repeated title and abstract terms because "
            "structured keywords/topics were unavailable in the materialized KG."
        )
        return text_fallback
    return data


def _build_theme_chart_payload(papers: List[UnifiedPaperEntity], *, output_dir: Path) -> Dict[str, Any]:
    ungated_theme_treemap = _build_themes(papers, apply_quality_gate=False)
    gated_theme_treemap = _build_themes(papers, apply_quality_gate=True)
    raw_theme_treemap = ungated_theme_treemap if not gated_theme_treemap.get("themes") else gated_theme_treemap
    request_payload, theme_postprocess = build_theme_postprocess_request(
        gated_theme_treemap,
        papers,
        report_mode="full",
    )
    result_payload = _load_json_if_exists(output_dir / THEME_POSTPROCESS_RESULT_FILENAME)
    if result_payload is not None:
        theme_treemap, theme_postprocess = apply_theme_postprocess_result(
            gated_theme_treemap,
            result_payload,
            model_label="host-agent",
        )
    else:
        theme_treemap = gated_theme_treemap
    if request_payload:
        _dump(output_dir / THEME_POSTPROCESS_REQUEST_FILENAME, request_payload)
    return {
        "raw_theme_treemap": raw_theme_treemap,
        "theme_treemap": theme_treemap,
        "theme_postprocess": theme_postprocess,
        "theme_postprocess_request": request_payload,
    }


def _source_label(source: str) -> str:
    labels = {
        "vpnsci-search-session": "seed",
        "vpnsci_seed": "seed",
        "seed": "seed",
        "openalex": "OpenAlex",
        "semantic_scholar": "Semantic Scholar",
        "semanticscholar": "Semantic Scholar",
        "s2": "Semantic Scholar",
        "crossref": "CrossRef",
        "pubmed": "PubMed",
        "arxiv": "arXiv",
    }
    raw = (source or "").strip()
    return labels.get(raw.lower(), raw)


def _actual_query_groups_from_query_plan(
    query_plan: List[Dict],
    *,
    user_query: str = "",
) -> List[Dict]:
    groups: Dict[str, List[str]] = {}
    normalized_user_query = (user_query or "").strip()

    def add(source: str, query: str) -> None:
        text = (query or "").strip()
        label = _source_label(source)
        if not label or not text:
            return
        if label == "seed" and normalized_user_query and text == normalized_user_query:
            return
        values = groups.setdefault(label, [])
        if text not in values:
            values.append(text)

    for item in query_plan:
        if not isinstance(item, dict):
            continue
        source = item.get("source") or item.get("database") or item.get("backend")
        query = item.get("text") or item.get("query") or item.get("search_string") or ""
        sources: List[str] = []
        if source:
            if str(source).strip().lower() == "both":
                sources.extend(["openalex", "semantic_scholar"])
            else:
                sources.append(str(source))
        else:
            if item.get("openalex") or item.get("boolean_openalex"):
                sources.append("openalex")
            if item.get("semantic_scholar") or item.get("boolean_ss"):
                sources.append("semantic_scholar")
            if not sources:
                sources.append("seed")
        for source_name in sources:
            add(source_name, str(query))

    ordered: List[Dict] = []
    for source in ["OpenAlex", "Semantic Scholar", "CrossRef", "PubMed", "arXiv", "seed"]:
        queries = groups.pop(source, None)
        if queries:
            ordered.append({"source": source, "queries": queries})
    for source, queries in groups.items():
        if queries:
            ordered.append({"source": source, "queries": queries})
    return ordered


# ---------- Paper rendering ----------

def _authors_short(p: UnifiedPaperEntity) -> str:
    if not p.authors:
        return ""
    names = [a.name for a in p.authors if a.name]
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]}, {names[1]}"
    if len(names) <= 4:
        return ", ".join(names[:-1]) + f", & {names[-1]}"
    return f"{names[0]} et al."


def _render_paper(p: UnifiedPaperEntity) -> Dict[str, Any]:
    valid_rcs = _rcs_value_if_valid(p)
    return {
        "paper_id": p.paper_id,
        "title": p.title or "(untitled)",
        "authors_short": _authors_short(p),
        "authors_full": [a.name for a in p.authors] if p.authors else [],
        "year": p.year,
        "venue": p.venue,
        "doi": p.doi,
        "doi_url": p.doi_url or (f"https://doi.org/{p.doi}" if p.doi else None),
        "abstract": p.abstract,
        "tldr": p.tldr,
        "rcs": p.rcs,
        "rcs_reasoning": p.rcs_reasoning,
        "rcs_flag": p.rcs_flag,
        "rcs_valid": valid_rcs is not None,
        "rcs_source": _rcs_source_for_paper(p),
        "citation_count": p.citation_count or 0,
        "influential_citation_count": p.influential_citation_count,
        "discovery_path": p.discovery_path,
        "sources": p.sources,
        "is_oa": p.is_oa,
    }


def _sorted_for_display(papers: List[UnifiedPaperEntity]) -> List[UnifiedPaperEntity]:
    """Display order: highly relevant first, then by citation count."""
    return sorted(papers, key=lambda p: (-(_rcs_value_if_valid(p) or 0), -(p.citation_count or 0), p.year or 0))


def _rcs_value_if_valid(p: UnifiedPaperEntity) -> Optional[int]:
    if p.rcs is None:
        return None
    if p.rcs_flag in INVALID_RCS_FLAGS:
        return None
    if p.rcs_valid is False:
        return None
    try:
        rcs = int(p.rcs)
    except (TypeError, ValueError):
        return None
    if 0 <= rcs <= 10:
        return rcs
    return None


def _rcs_source_for_paper(p: UnifiedPaperEntity) -> str:
    if p.rcs is None:
        return p.rcs_source or "none"
    if p.rcs_flag in INVALID_RCS_FLAGS:
        return "parser_fallback"
    if p.rcs_valid is False:
        return p.rcs_source or "none"
    return p.rcs_source or "full_classifier"


def _rcs_coverage_metadata(
    papers: List[UnifiedPaperEntity],
    *,
    rcs_execution_mode: str,
) -> Dict[str, Any]:
    mode = (rcs_execution_mode or "none").strip()
    if mode not in VALID_RCS_EXECUTION_MODES:
        raise ValueError(
            "rcs_execution_mode must be one of: "
            + ", ".join(sorted(VALID_RCS_EXECUTION_MODES))
        )
    valid_count = sum(1 for p in papers if _rcs_value_if_valid(p) is not None)
    total_count = len(papers)
    if valid_count:
        notice = (
            "RCS covers the full workflow result set; classification was executed serially by the main host Agent."
            if mode == "main_agent_serial"
            else "RCS covers the full workflow result set."
        )
    else:
        notice = (
            "Formal RCS classification was attempted, but no valid RCS scores were produced."
            if mode != "none"
            else "RCS is unavailable for this report."
        )
    return {
        "rcs_execution_mode": mode if valid_count or mode != "none" else "none",
        "rcs_scope": "full_workflow" if valid_count else "none",
        "rcs_valid_count": valid_count,
        "rcs_total_count": total_count,
        "rcs_notice": notice,
    }


# ---------- Metadata ----------

def _build_metadata(
    *,
    kg: Dict[str, UnifiedPaperEntity],
    classified: List[UnifiedPaperEntity],
    discovery_curve: Dict[str, Any],
    user_query: str,
    tier: str,
    search_id: str,
    wall_clock_seconds: Optional[float],
    stop_reason: Optional[str],
    query_plan: Optional[List[Dict]] = None,
    rcs_execution_mode: str = "subagent_parallel",
) -> Dict[str, Any]:
    valid_rcs_values = [
        rcs
        for p in classified
        for rcs in [_rcs_value_if_valid(p)]
        if rcs is not None
    ]
    highly_relevant = sum(1 for rcs in valid_rcs_values if rcs >= 7)
    closely_related = sum(1 for rcs in valid_rcs_values if rcs in (5, 6))
    # P0-7 fix: use explicit None check so a real 0.0 still renders 0.0 and a
    # genuine resolved value (e.g. mtime fallback) survives.
    wall_clock = (
        round(float(wall_clock_seconds), 1)
        if wall_clock_seconds is not None
        else 0.0
    )
    query_plan = query_plan or []
    actual_query_groups = _actual_query_groups_from_query_plan(
        query_plan,
        user_query=user_query,
    )
    metadata = {
        "search_id": search_id,
        "query": user_query,
        "tier": tier,
        "wall_clock_total_s": wall_clock,
        "papers_evaluated": len(classified),
        "papers_in_kg": len(kg),
        "highly_relevant_count": highly_relevant,
        "closely_related_count": closely_related,
        "coverage_estimate": discovery_curve.get("coverage_estimate"),
        "coverage_ci": [
            discovery_curve.get("ci_low"),
            discovery_curve.get("ci_high"),
        ],
        "generated_at": datetime.now().isoformat(),
        "skill_version": "paper-search-pro/2.0",
        "stop_reason": stop_reason,
        **_rcs_coverage_metadata(
            classified,
            rcs_execution_mode=rcs_execution_mode,
        ),
    }
    if actual_query_groups:
        metadata["user_query"] = user_query
        metadata["display_query"] = user_query
        metadata["query_display"] = {
            "user_query": user_query,
            "primary": user_query,
            "actual_queries": actual_query_groups,
        }
    return metadata


# ---------- CLI ----------

def _kg_from_json(payload) -> Dict[str, UnifiedPaperEntity]:
    """Decode kg.json into Dict[str, UnifiedPaperEntity]."""
    from .types import Author

    def _paper(d: Dict) -> UnifiedPaperEntity:
        authors = [
            Author(
                name=a.get("name", "") if isinstance(a, dict) else str(a),
                orcid=a.get("orcid") if isinstance(a, dict) else None,
                affiliation=a.get("affiliation") if isinstance(a, dict) else None,
                country=a.get("country") if isinstance(a, dict) else None,
                is_first=bool(a.get("is_first")) if isinstance(a, dict) else False,
                is_corresponding=bool(a.get("is_corresponding")) if isinstance(a, dict) else False,
            )
            for a in (d.get("authors") or [])
        ]
        return UnifiedPaperEntity(
            doi=d.get("doi"),
            arxiv_id=d.get("arxiv_id"),
            openalex_id=d.get("openalex_id"),
            ss_paper_id=d.get("ss_paper_id"),
            pmid=d.get("pmid"),
            title=d.get("title", "") or "",
            abstract=d.get("abstract"),
            authors=authors,
            year=d.get("year"),
            venue=d.get("venue"),
            type=d.get("type"),
            citation_count=int(d.get("citation_count") or 0),
            fwci=d.get("fwci"),
            topics=list(d.get("topics") or []),
            keywords=list(d.get("keywords") or []),
            influential_citation_count=d.get("influential_citation_count"),
            tldr=d.get("tldr"),
            doi_url=d.get("doi_url"),
            rcs=d.get("rcs"),
            rcs_reasoning=d.get("rcs_reasoning"),
            rcs_flag=d.get("rcs_flag"),
            rcs_valid=d.get("rcs_valid"),
            rcs_source=d.get("rcs_source"),
            sources=list(d.get("sources") or []),
            discovery_path=d.get("discovery_path"),
            is_oa=d.get("is_oa"),
        )

    kg: Dict[str, UnifiedPaperEntity] = {}
    if isinstance(payload, dict):
        for k, v in payload.items():
            if isinstance(v, dict):
                kg[str(k)] = _paper(v)
    elif isinstance(payload, list):
        for d in payload:
            if not isinstance(d, dict):
                continue
            paper = _paper(d)
            kg[paper.paper_id] = paper
    return kg


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description=(
            "Materialize a classified KG into report_data.json + sibling "
            "chart_data.json / paper_list.json / metadata.json / prisma_log.json."
        )
    )
    parser.add_argument(
        "--kg",
        required=True,
        type=Path,
        help="Path to kg_classified.json.",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        help="Path to the executive summary markdown (written by main agent).",
    )
    parser.add_argument(
        "--query",
        default="",
        help="Original user query string.",
    )
    parser.add_argument(
        "--tier",
        default="standard",
        help="Tier name (quick/standard/deep/audit).",
    )
    parser.add_argument(
        "--search-id",
        default="",
        help="Optional search ID.",
    )
    parser.add_argument(
        "--snapshots",
        type=Path,
        help="Optional path to discovery_curve_snapshots.json.",
    )
    parser.add_argument(
        "--query-plan",
        type=Path,
        help=(
            "Optional path to query_plan.json/list. When provided, metadata "
            "records source-specific actual search queries for the HTML Hero."
        ),
    )
    parser.add_argument(
        "--wall-clock-seconds",
        type=float,
        help="Optional wall-clock elapsed time (seconds). Highest priority.",
    )
    parser.add_argument(
        "--started-at",
        default=None,
        help=(
            "Optional ISO timestamp recording when the main agent's STEP 1 "
            "began. Used to compute wall_clock when --wall-clock-seconds is "
            "absent (P0-7)."
        ),
    )
    parser.add_argument(
        "--rcs-execution-mode",
        choices=sorted(VALID_RCS_EXECUTION_MODES),
        default="subagent_parallel",
        help=(
            "How formal RCS classification was executed. Use main_agent_serial "
            "only after explicit serial fallback."
        ),
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path to report_data.json (its parent directory receives the sibling files).",
    )
    args = parser.parse_args()

    if not args.kg.exists():
        sys.exit(f"data_materialization: KG not found at {args.kg}")

    kg = _kg_from_json(json.loads(args.kg.read_text(encoding="utf-8")))
    if not kg:
        sys.exit(f"data_materialization: empty KG loaded from {args.kg}")

    summary_text = ""
    if args.summary and args.summary.exists():
        summary_text = args.summary.read_text(encoding="utf-8")

    snapshots: List[Dict] = []
    if args.snapshots and args.snapshots.exists():
        loaded = json.loads(args.snapshots.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            snapshots = [loaded]
        elif isinstance(loaded, list):
            snapshots = [s for s in loaded if isinstance(s, dict)]

    query_plan: List[Dict] = []
    if args.query_plan and args.query_plan.exists():
        loaded_query_plan = json.loads(args.query_plan.read_text(encoding="utf-8"))
        if isinstance(loaded_query_plan, list):
            query_plan = [q for q in loaded_query_plan if isinstance(q, dict)]
        elif isinstance(loaded_query_plan, dict):
            strategies = loaded_query_plan.get("strategies")
            if isinstance(strategies, list):
                query_plan = [q for q in strategies if isinstance(q, dict)]
            else:
                query_plan = [loaded_query_plan]

    output_dir = args.output.parent
    artifacts = materialize(
        kg,
        output_dir,
        user_query=args.query,
        tier=args.tier,
        search_id=args.search_id,
        summary=summary_text,
        query_plan=query_plan,
        discovery_curve_snapshots=snapshots,
        wall_clock_seconds=args.wall_clock_seconds,
        started_at=args.started_at,
        # P0-7 graceful fallback: when neither --wall-clock-seconds nor
        # --started-at is passed, fall back to kg.json mtime so metadata
        # carries a non-zero (approximate) wall_clock.
        kg_source_path=args.kg,
        rcs_execution_mode=args.rcs_execution_mode,
    )
    # If --output names a file other than report_data.json, point it there.
    if args.output.name != "report_data.json":
        args.output.write_text(
            artifacts["report_data"].read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    for name, path in artifacts.items():
        print(f"data_materialization: {name} -> {path}")
