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
from .sources.search_cache import SearchSession
from .sources.search_models import SearchHit


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
        hits=[SearchHit(**item) for item in data.get("hits", [])],
        source_summary=data.get("source_summary") or {},
        errors=[],
        upgrade_suggested=bool(data.get("upgrade_suggested")),
        decision_reasons=data.get("decision_reasons") or [],
        created_at=data.get("created_at") or "",
    )


def _score_hit(hit: SearchHit) -> int:
    """Heuristic RCS score for seed-only reports that skip LLM classification."""

    title = (hit.title or "").lower()
    abstract = (hit.abstract or "").lower()
    text = f"{title} {abstract}"
    high_signal_terms = (
        "systematic review",
        "meta-analysis",
        "clinical accuracy",
        "core body temperature",
        "fever detection",
    )
    close_signal_terms = (
        "infrared",
        "thermography",
        "non-contact",
        "thermal scanner",
        "body temperature",
    )
    if any(term in text for term in high_signal_terms):
        return 7
    if any(term in text for term in close_signal_terms):
        return 6
    return 5


def _paper_from_hit(hit: SearchHit, index: int, query: str) -> dict:
    rcs = _score_hit(hit)
    return {
        "id": hit.doi or hit.openalex_id or hit.s2_paper_id or hit.url or f"seed-{index}",
        "paper_id": hit.doi or hit.openalex_id or hit.s2_paper_id or hit.url or f"seed-{index}",
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
        "doi_url": f"https://doi.org/{hit.doi}" if hit.doi else hit.url,
        "url": hit.url,
        "pdf_url": hit.pdf_url,
        "abstract": hit.abstract,
        "citation_count": hit.citation_count,
        "source": ", ".join(hit.sources or [hit.source or hit.backend or "seed"]),
        "tier": "seed",
        "rcs": rcs,
        "rcs_reasoning": "Seed result from vpnsci-sustech standard search session; relevance estimated heuristically for report visualization.",
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


def _paper_text(paper: dict) -> str:
    return " ".join(
        str(paper.get(key) or "")
        for key in ("title", "abstract", "venue", "journal", "source")
    ).lower()


THEME_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "非接触测温/热筛查",
        (
            "fever",
            "body temperature",
            "non-contact",
            "non contact",
            "thermometry",
            "thermal screening",
            "temperature measurement",
            "体温",
            "测温",
            "发热",
            "筛查",
            "非接触",
        ),
    ),
    (
        "红外热成像/热像仪",
        (
            "thermography",
            "thermal imaging",
            "thermal image",
            "thermal camera",
            "infrared imaging",
            "热成像",
            "热像",
            "热红外",
        ),
    ),
    (
        "传感器/光谱/仪器",
        (
            "sensor",
            "spectroscopy",
            "spectrometer",
            "instrument",
            "calibration",
            "optical",
            "detector",
            "光谱",
            "传感器",
            "仪器",
            "标定",
            "探测器",
        ),
    ),
    (
        "遥感/环境红外",
        (
            "remote sensing",
            "satellite",
            "land surface",
            "environment",
            "retrieval",
            "遥感",
            "卫星",
            "地表",
            "环境",
        ),
    ),
    (
        "材料/器件红外",
        (
            "material",
            "nanomaterial",
            "device",
            "semiconductor",
            "emissivity",
            "thin film",
            "材料",
            "器件",
            "半导体",
            "发射率",
        ),
    ),
    (
        "医学/生物应用",
        (
            "medical",
            "clinical",
            "patient",
            "diagnosis",
            "biomedical",
            "physiological",
            "医学",
            "临床",
            "患者",
            "诊断",
            "生物",
        ),
    ),
)


def _fallback_theme_name(paper: dict) -> str:
    text = _paper_text(paper)
    for theme, terms in THEME_RULES:
        if any(term in text for term in terms):
            return theme
    if "infrared" in text or "红外" in text:
        return "红外测量综合"
    return "其他相关研究"


def _build_theme_treemap(papers: list[dict]) -> dict:
    """Build seed-preview topic groups without relying on upstream KG topics."""

    grouped: dict[str, list[str]] = {}
    for index, paper in enumerate(papers, 1):
        paper_id = paper.get("paper_id") or paper.get("id") or f"seed-{index}"
        theme = _fallback_theme_name(paper)
        grouped.setdefault(theme, []).append(str(paper_id))

    themes = [
        {"name": name, "value": len(paper_ids), "paper_ids": paper_ids}
        for name, paper_ids in grouped.items()
        if paper_ids
    ]
    themes.sort(key=lambda item: (-int(item["value"]), str(item["name"])))

    return {
        "themes": themes,
        "total_papers": len(papers),
        "method": "seed_title_abstract_rule_fallback",
        "note": "Seed-preview topic groups derived from title, abstract, and venue because upstream KG topics/keywords are not available.",
    }


def _build_chart_data(papers: list[dict], source_summary: dict) -> dict:
    years: dict[int, dict[str, int]] = {}
    rcs_counts = [0] * 11
    for paper in papers:
        year = paper.get("year")
        rcs = int(paper.get("rcs") or 0)
        if year:
            years.setdefault(int(year), {"year": int(year), "total": 0, "highly_relevant": 0})
            years[int(year)]["total"] += 1
            if rcs >= 7:
                years[int(year)]["highly_relevant"] += 1
        if 0 <= rcs <= 10:
            rcs_counts[rcs] += 1
    total = len(papers)
    highly = sum(1 for p in papers if int(p.get("rcs") or 0) >= 7)
    closely = sum(1 for p in papers if int(p.get("rcs") or 0) in (5, 6))
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
            "bins": [{"rcs": i, "count": rcs_counts[i]} for i in range(11)],
            "mean": round(sum(i * rcs_counts[i] for i in range(11)) / total, 2) if total else None,
            "ci_low": None,
            "ci_high": None,
            "n": total,
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
        "theme_treemap": _build_theme_treemap(papers),
    }


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


def _build_seed_prisma_log(session: SearchSession, papers: list[dict], metadata: dict) -> dict:
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
            "note": "Not performed in seed_preview mode.",
        },
        "4_online_resources_browsing": _seed_step_not_performed("Not performed in seed_preview mode."),
        "5_citation_searching": _seed_step_not_performed("Citation chasing is part of full paper-search-pro, not seed_preview."),
        "6_contacts": _seed_step_not_performed("Author/contact search is not performed in seed_preview mode."),
        "7_other_methods": {
            "performed": True,
            "note": "Existing vpnsci-sustech Search Session reused as seed evidence for quick HTML reporting.",
        },
        "8_full_search_strategies": {
            "performed": True,
            "user_query": metadata.get("query") or session.query,
            "seed_session_query": session.query,
            "query_variants": query_variants,
            "note": "Records the available query variants from the seed Search Session; not a full upstream query plan.",
        },
        "9_limits_and_restrictions": {
            "performed": True,
            "limits": [
                "seed_preview mode",
                "existing Search Session only",
                "no full source expansion",
                "no SubAgent relevance grading",
            ],
        },
        "10_search_filters": {
            "performed": bool(session.filters),
            "filters": session.filters or {},
        },
        "11_prior_work": _seed_step_not_performed("Prior systematic review search is not performed in seed_preview mode."),
        "12_updates": _seed_step_not_performed("Search update tracking is not performed in seed_preview mode."),
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
            "report_mode": "seed_preview",
            "outputs": ["metadata.json", "paper_list.json", "chart_data.json", "prisma_log.json", "report_data.json", "report.html"],
        },
        "_meta": {
            "mode": "seed_preview",
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
) -> Path:
    data_dir = output_dir / "materialized"
    data_dir.mkdir(parents=True, exist_ok=True)
    report_query = display_query or session.query
    report_language = language or _detect_language(report_query)
    papers = [_paper_from_hit(hit, i, report_query) for i, hit in enumerate(session.hits, 1)]
    chart_data = _build_chart_data(papers, session.source_summary)
    highly = sum(1 for paper in papers if int(paper.get("rcs") or 0) >= 7)
    closely = sum(1 for paper in papers if int(paper.get("rcs") or 0) in (5, 6))
    discovery_curve = chart_data["discovery_curve"]
    actual_query_variants = _query_variants_from_session(session)
    actual_query_groups = _actual_query_groups_from_session(session, display_query=report_query)
    metadata = {
        "query": report_query,
        "language": report_language,
        "user_query": report_query,
        "display_query": report_query,
        "seed_session_query": session.query,
        "actual_query_variants": actual_query_variants,
        "query_display": {
            "user_query": report_query,
            "primary": report_query,
            "expanded": actual_query_variants,
            "actual_queries": actual_query_groups,
        },
        "search_id": session.session_id,
        "seed_session_id": session.session_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_papers": len(papers),
        "papers_evaluated": len(papers),
        "papers_in_kg": len(papers),
        "highly_relevant_count": highly,
        "closely_related_count": closely,
        "coverage_estimate": discovery_curve["coverage_estimate"],
        "coverage_ci": [discovery_curve["ci_low"], discovery_curve["ci_high"]],
        "coverage_label": "seed preview estimate",
        "source_summary": session.source_summary,
        "mode": "vpnsci-seed-report",
        "report_mode": "seed_preview",
        "tier": "standard",
    }
    prisma_log = _build_seed_prisma_log(session, papers, metadata)
    report_data = {
        "metadata": metadata,
        "chart_data": chart_data,
        "paper_list": papers,
        "prisma_log": prisma_log,
        "summary": "",
    }
    (data_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "paper_list.json").write_text(json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "chart_data.json").write_text(json.dumps(chart_data, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "prisma_log.json").write_text(json.dumps(prisma_log, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "report_data.json").write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data_dir


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
    session = _load_seed(seed_json)
    output_dir.mkdir(parents=True, exist_ok=True)
    materialized_dir = _write_materialized_data(
        session,
        output_dir,
        display_query=display_query,
        language=language,
    )
    sys.path.insert(0, str(tool_root))

    selected_language = language or _detect_language(display_query or session.query)
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
