"""Adapter that renders a vpnsci search session with bundled paper-search-pro assets."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from .config import Config
from .sources.search_cache import SearchSession
from .sources.search_models import SearchHit


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


def _paper_from_hit(hit: SearchHit, index: int) -> dict:
    return {
        "id": hit.doi or hit.openalex_id or hit.s2_paper_id or hit.url or f"seed-{index}",
        "title": hit.title,
        "authors": hit.authors,
        "year": hit.year,
        "venue": hit.journal,
        "doi": hit.doi,
        "url": hit.url,
        "pdf_url": hit.pdf_url,
        "abstract": hit.abstract,
        "citation_count": hit.citation_count,
        "source": ", ".join(hit.sources or [hit.source or hit.backend or "seed"]),
        "tier": "seed",
        "rcs": 1.0,
        "rcs_reasoning": "Seed result from vpnsci-sustech standard search session.",
    }


def _write_materialized_data(session: SearchSession, output_dir: Path) -> Path:
    data_dir = output_dir / "materialized"
    data_dir.mkdir(parents=True, exist_ok=True)
    language = _detect_language(session.query)
    papers = [_paper_from_hit(hit, i) for i, hit in enumerate(session.hits, 1)]
    years: dict[str, int] = {}
    for hit in session.hits:
        if hit.year:
            years[str(hit.year)] = years.get(str(hit.year), 0) + 1
    metadata = {
        "query": session.query,
        "language": language,
        "seed_session_id": session.session_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_papers": len(papers),
        "source_summary": session.source_summary,
        "mode": "vpnsci-seed-report",
    }
    chart_data = {
        "year_counts": years,
        "source_summary": session.source_summary,
        "total_papers": len(papers),
    }
    prisma_log = {
        "seed": {
            "status": "completed",
            "records": len(papers),
            "note": "Generated from existing vpnsci-sustech search session.",
        }
    }
    (data_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "paper_list.json").write_text(json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "chart_data.json").write_text(json.dumps(chart_data, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "prisma_log.json").write_text(json.dumps(prisma_log, ensure_ascii=False, indent=2), encoding="utf-8")
    return data_dir


def render_report(seed_json: Path, output_dir: Path) -> Path:
    config = Config.load()
    tool_root = Path(config.paper_search_pro_root)
    if not tool_root.exists():
        raise FileNotFoundError(f"paper-search-pro local runtime not found: {tool_root}")
    session = _load_seed(seed_json)
    output_dir.mkdir(parents=True, exist_ok=True)
    materialized_dir = _write_materialized_data(session, output_dir)
    sys.path.insert(0, str(tool_root))
    from scripts.html_renderer_webartifacts import render_html_webartifacts

    report_path = output_dir / "report.html"
    render_html_webartifacts(
        materialized_data_dir=materialized_dir,
        output_path=report_path,
        user_query=session.query,
        language=_detect_language(session.query),
    )
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render vpnsci seed session with paper-search-pro assets")
    parser.add_argument("--seed", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    report = render_report(args.seed, args.output_dir)
    print(f"report.html: {report}")


if __name__ == "__main__":
    main()
