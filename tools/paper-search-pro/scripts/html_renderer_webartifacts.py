"""HTML renderer (web-artifacts-builder + Shadcn path).

Reads the four JSON files produced by data_materialization.py + prisma_s_logger,
maps them into the schema expected by the React App.tsx, then injects them as
`window.__REPORT_DATA__` into a pre-built bundle.html (shipped in assets/).

Raises HtmlRenderError if the pre-built bundle is missing.

Design notes (2026-05-23):
  * No size-driven fallback. Earlier versions degraded to a leaner jinja2
    template when the bundle exceeded a threshold — that created inconsistent
    UX (same Skill produced two different visual reports depending on data
    size). Removed entirely. Modern browsers open 10+ MB HTML files without
    issue; a 1.7 MB self-contained academic report is well within comfort.
  * No oversize sidecar advisories. Users don't care that a report is
    "1.6 MB" — they care that it opens cleanly.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

SKILL_ROOT = Path(__file__).resolve().parent.parent
PREBUILT_BUNDLE = (
    SKILL_ROOT / "assets" / "webartifacts_app" / "paper-report" / "bundle.html"
)


class HtmlRenderError(RuntimeError):
    """Raised when the webartifacts pipeline cannot produce a valid HTML file."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_html_webartifacts(
    materialized_data_dir: Path,
    output_path: Path,
    *,
    user_query: str = "",
    language: Optional[str] = None,
) -> Path:
    """Render a Shadcn-styled HTML report by hydrating the pre-built bundle.

    Strategy:
      1. Read the four JSON files from materialized_data_dir.
      2. Pass them through as the raw shape expected by React `normalize()`.
      3. Read assets/webartifacts_app/paper-report/bundle.html (pre-built once).
      4. Inject `<script>window.__REPORT_LANG__ = "..."</script>` AND
         `<script>window.__REPORT_DATA__ = {...};</script>` before the first
         existing <script> tag (the LANG one comes first so the React bundle's
         `installLanguage()` call picks it up before any component renders).
      5. Write to output_path.

    Args:
        materialized_data_dir: directory containing the four JSON files.
        output_path: where to write the hydrated HTML.
        user_query: fallback query string when metadata lacks one.
        language: "en" or "zh". Resolution order:
            (a) explicit `language` argument, (b) `metadata.language`,
            (c) "en". Anything else falls back to "en" with a console warning
            inside the React bundle. The bundle ships with both `STRINGS.en`
            and `STRINGS.zh` dictionaries; this flag picks which one mounts.
    """
    materialized_data_dir = Path(materialized_data_dir)
    output_path = Path(output_path)

    if not PREBUILT_BUNDLE.exists():
        raise HtmlRenderError(
            f"Pre-built bundle not found at {PREBUILT_BUNDLE}. "
            "Run web-artifacts-builder bundle-artifact.sh first."
        )

    metadata = _read_json(materialized_data_dir / "metadata.json")
    paper_list = _read_json(materialized_data_dir / "paper_list.json")
    chart_data = _read_json(materialized_data_dir / "chart_data.json")
    prisma_log_raw = _read_json(materialized_data_dir / "prisma_log.json")
    report_bundle = _read_optional_json(materialized_data_dir / "report_data.json")
    report_summary = ""
    if isinstance(report_bundle, dict):
        report_summary = str(report_bundle.get("summary") or "")

    metadata, chart_data = _apply_payload_compat(
        metadata=metadata,
        paper_list=paper_list,
        chart_data=chart_data,
        user_query=user_query,
    )

    # Resolve language: explicit > metadata.language > "en"
    resolved_lang = _resolve_language(language, metadata)

    report_data = _build_report_data(
        metadata=metadata,
        paper_list=paper_list,
        chart_data=chart_data,
        prisma_log_raw=prisma_log_raw,
        user_query=user_query,
        summary=report_summary,
    )

    bundle_html = PREBUILT_BUNDLE.read_text(encoding="utf-8")
    bundle_html = _inject_actual_query_strip_compat(bundle_html)
    # Inject DATA first then LANG, so LANG ends up FIRST in the HTML stream
    # (each _inject_* helper inserts before the current first <script>; the
    # second call therefore lands before the script written by the first
    # call). This matches the docstring's claim that LANG comes first.
    hydrated_html = _inject_report_data(bundle_html, report_data)
    hydrated_html = _inject_language(hydrated_html, resolved_lang)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(hydrated_html, encoding="utf-8")

    log.info(
        "Webartifacts HTML rendered: %s (%.0f KB)",
        output_path,
        output_path.stat().st_size / 1024,
    )
    return output_path


# ---------------------------------------------------------------------------
# Mapping: paper-search-pro JSON  ->  App.tsx schema
# ---------------------------------------------------------------------------

def _build_report_data(
    metadata: Dict[str, Any],
    paper_list: List[Dict[str, Any]],
    chart_data: Dict[str, Any],
    prisma_log_raw: Dict[str, Any],
    *,
    user_query: str = "",
    summary: str = "",
) -> Dict[str, Any]:
    """Build the raw-shape payload that React's `normalize(raw)` expects.

    React reads four top-level keys from `window.__REPORT_DATA__`:
    `{metadata, papers, chart_data, prisma_log}` — the same shape produced by
    `data_materialization.py` and validated by the `sample-standard.json`
    fixture in the React app's design assets. The earlier post-materialization
    schema (`reportMeta` / `themes` / `prismaLog`) was a dead branch that
    matched no React surface, leaving Hero / Methods / Audit blank on real
    data even though Mock-data baseline rendered correctly.

    Transformations applied here:
      * `metadata` — pass through; fill in `query` from CLI fallback if missing.
      * `papers` — pass through with ALL fields intact, including `abstract`
        and `rcs_reasoning`. PaperSheet renders an Abstract section (collapsed
        by default, expandable) and a "Why this paper" section (rcs_reasoning).
        Earlier optimization stripped both to keep the hydrated bundle below a
        1500 KB auto-fallback threshold, but two reviewers independently
        confirmed it crippled the research workflow (TLDR is AI-generated,
        not a substitute for the original abstract; rcs_reasoning has no
        substitute). Bundle is now allowed to grow to ~1.6 MB on 250-paper
        reports — within the new 2500 KB threshold.
      * `chart_data` + `prisma_log` — pass through verbatim. React's
        `parsePrismaPythonRepr` already handles Python-style dict repr
        strings inside step values, and the dict-of-step-key shape matches
        what `prisma_s_logger.build_prisma_s_log` emits.
    """
    # Query fallback (legacy data dirs that lacked the `query` key in metadata).
    meta_out: Dict[str, Any] = dict(metadata) if isinstance(metadata, dict) else {}
    if not meta_out.get("query") and user_query:
        meta_out["query"] = user_query
    if not meta_out.get("summary") and summary:
        meta_out["summary"] = summary

    return {
        "metadata": meta_out,
        "summary": meta_out.get("summary") or summary or "",
        "papers": list(paper_list) if isinstance(paper_list, list) else [],
        "chart_data": chart_data if isinstance(chart_data, dict) else {},
        "prisma_log": prisma_log_raw if isinstance(prisma_log_raw, dict) else {},
    }


def _apply_payload_compat(
    *,
    metadata: Dict[str, Any],
    paper_list: List[Dict[str, Any]],
    chart_data: Dict[str, Any],
    user_query: str = "",
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Backfill renderer-facing compatibility fields for full/recovery payloads.

    `seed_preview` already emits a richer contract from
    `vpnsci_sustech.light_report_bridge`. Full/recovery flows may only
    carry the lean upstream materialization shape. This shim fills the
    renderer-facing gaps while preserving any stronger upstream truth.
    """

    meta_out: Dict[str, Any] = dict(metadata) if isinstance(metadata, dict) else {}
    chart_out: Dict[str, Any] = dict(chart_data) if isinstance(chart_data, dict) else {}
    papers: List[Dict[str, Any]] = list(paper_list) if isinstance(paper_list, list) else []

    resolved_query = (
        str(
            meta_out.get("query")
            or meta_out.get("display_query")
            or meta_out.get("user_query")
            or user_query
            or ""
        ).strip()
    )
    if resolved_query:
        meta_out.setdefault("query", resolved_query)
        meta_out.setdefault("original_query", resolved_query)
        meta_out.setdefault("user_query", resolved_query)
        meta_out.setdefault("display_query", resolved_query)
        meta_out.setdefault("seed_session_query", resolved_query)

    # metadata/query-display compatibility
    query_display = dict(meta_out.get("query_display") or {})
    query_display.setdefault("user_query", resolved_query)
    query_display.setdefault("primary", resolved_query)
    actual_queries = list(query_display.get("actual_queries") or [])
    query_display["actual_queries"] = actual_queries

    actual_query_variants = list(meta_out.get("actual_query_variants") or [])
    if not actual_query_variants and actual_queries:
        for group in actual_queries:
            for query in group.get("queries") or []:
                text = str(query or "").strip()
                if text:
                    actual_query_variants.append(
                        {
                            "type": "original" if text == resolved_query else "expanded",
                            "query": text,
                        }
                    )
    if actual_query_variants and not query_display.get("expanded"):
        query_display["expanded"] = actual_query_variants
    meta_out["query_display"] = query_display
    if actual_query_variants:
        meta_out.setdefault("actual_query_variants", actual_query_variants)

    # metadata defaults aligned with seed-preview compatibility contract
    meta_out.setdefault("language", _detect_language(resolved_query))
    meta_out.setdefault("seed_source", _seed_source_label(papers))
    meta_out.setdefault("cnki_fields", _cnki_field_status_from_papers(papers))
    meta_out.setdefault("recovered_label", "")
    meta_out.setdefault("report_label_mode", "检索结果")
    meta_out.setdefault("missing_fields", [])
    meta_out.setdefault("insufficient_analysis_fields", [])
    meta_out.setdefault("seed_session_id", meta_out.get("search_id") or "")
    meta_out.setdefault("total_papers", len(papers))
    meta_out.setdefault("coverage_label", "compat estimate")
    meta_out.setdefault("source_summary", _source_summary_from_papers(papers))
    meta_out.setdefault("mode", "vpnsci-compat-report")
    meta_out.setdefault("report_mode", "full")

    # chart-data compatibility aligned with seed-preview outputs
    publication_year = chart_out.get("publication_year") or {}
    bins = publication_year.get("bins") or []
    if "year_counts" not in chart_out and isinstance(bins, list):
        chart_out["year_counts"] = {
            str(item.get("year")): int(item.get("total") or 0)
            for item in bins
            if isinstance(item, dict) and item.get("year") is not None
        }
    chart_out.setdefault("source_summary", meta_out.get("source_summary") or _source_summary_from_papers(papers))
    chart_out.setdefault("total_papers", len(papers))
    if isinstance(chart_out.get("theme_treemap"), dict):
        chart_out["theme_treemap"].setdefault("method", "compat_renderer_fallback")
        chart_out["theme_treemap"].setdefault(
            "note",
            "Compatibility metadata injected by html_renderer_webartifacts so lean full/recovery payloads stay renderable under the same frontend contract as seed_preview.",
        )

    return meta_out, chart_out


def _detect_language(query: str) -> str:
    return "zh" if any("\u4e00" <= ch <= "\u9fff" for ch in query or "") else "en"


def _source_summary_from_papers(papers: List[Dict[str, Any]]) -> Dict[str, int]:
    summary: Dict[str, int] = {}
    for paper in papers:
        raw_sources = paper.get("sources") or []
        if isinstance(raw_sources, list) and raw_sources:
            sources = [str(source) for source in raw_sources if source]
        else:
            source_value = paper.get("source") or "openalex"
            sources = [part.strip() for part in str(source_value).split(",") if part.strip()] or ["openalex"]
        for source in sources:
            summary[source] = summary.get(source, 0) + 1
    return summary


def _seed_source_label(papers: List[Dict[str, Any]]) -> str:
    summary = _source_summary_from_papers(papers)
    active = [source for source, count in summary.items() if count]
    if active == ["cnki"]:
        return "cnki"
    if active:
        return "mixed" if len(active) > 1 else active[0]
    return "seed"


def _cnki_field_status_from_papers(papers: List[Dict[str, Any]]) -> Dict[str, Any]:
    fields = ["cnki_id", "source_url", "download_format", "local_file", "result_type"]
    cnki_like = []
    for paper in papers:
        sources = paper.get("sources") or []
        source = str(paper.get("source") or "")
        if (
            paper.get("cnki_id")
            or paper.get("source_url")
            or paper.get("download_format")
            or paper.get("local_file")
            or paper.get("result_type")
            or "cnki" in sources
            or source == "cnki"
        ):
            cnki_like.append(paper)
    return {
        "present": bool(cnki_like),
        "hit_count": len(cnki_like),
        "fields": fields,
        "preserved_counts": {
            field: sum(1 for paper in cnki_like if paper.get(field))
            for field in fields
        },
    }


# ---------------------------------------------------------------------------
# HTML hydration
# ---------------------------------------------------------------------------

_FIRST_SCRIPT_RE = re.compile(r"<script(\s|>)")


def _inject_report_data(bundle_html: str, report_data: Dict[str, Any]) -> str:
    """Insert `<script>window.__REPORT_DATA__ = ...</script>` before the first <script>."""
    payload = json.dumps(
        report_data,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    # Escape sequences that would prematurely close the script tag.
    safe_payload = payload.replace("</script>", "<\\/script>")
    injection = (
        f"<script>window.__REPORT_DATA__ = {safe_payload};</script>"
    )

    match = _FIRST_SCRIPT_RE.search(bundle_html)
    if not match:
        # No <script> in bundle? Append before </body>.
        if "</body>" in bundle_html:
            return bundle_html.replace("</body>", f"{injection}</body>", 1)
        return bundle_html + injection
    insert_at = match.start()
    return bundle_html[:insert_at] + injection + bundle_html[insert_at:]


def _inject_actual_query_strip_compat(bundle_html: str) -> str:
    """Add a small runtime guard for bundles built before the query-strip UI.

    The React source owns the component in current code, but some shipped
    `bundle.html` files are pre-built. This compatibility layer reads
    `metadata.query_display.actual_queries` from `window.__REPORT_DATA__` and
    inserts the same strip after the Hero H1 only when the React bundle has not
    already rendered `.psp-query-strip`.
    """
    marker = "data-psp-query-strip-compat"
    if marker in bundle_html:
        return bundle_html

    injection = r'''<style data-psp-query-strip-compat>
.psp-query-strip{margin-top:16px;max-width:100%;color:hsl(var(--muted-foreground));font-family:var(--font-sans)}
.rd-hero-swiss .psp-query-strip{max-width:min(680px,100%);margin-top:18px}
.rd-hero-editorial .psp-query-strip{margin-top:18px}
.rd-hero-document .psp-query-strip{margin-top:14px}
.psp-query-strip-kicker{font-family:var(--font-mono);font-size:10.5px;line-height:1;letter-spacing:.12em;text-transform:uppercase;color:hsl(var(--muted-foreground));margin-bottom:9px}
.psp-query-strip-grid{display:grid;grid-template-columns:max-content minmax(0,1fr);column-gap:10px;row-gap:7px;align-items:start;max-width:100%}
.psp-query-strip-row{display:contents}
.psp-query-strip-source{justify-self:end;display:inline-flex;align-items:center;min-height:21px;padding:2px 7px;border:1px solid hsl(var(--border));border-radius:999px;background:hsl(var(--background));color:hsl(var(--foreground));font-family:var(--font-mono);font-size:10.5px;line-height:1.2;letter-spacing:.01em;white-space:nowrap}
.psp-query-strip-chips{display:flex;flex-wrap:wrap;align-items:center;gap:5px;min-width:0}
.psp-query-strip-chip{display:inline-flex;align-items:center;max-width:100%;min-height:21px;padding:2px 7px;border:1px solid hsl(var(--border));border-radius:6px;background:hsl(var(--muted)/.46);color:hsl(var(--foreground));font-family:var(--font-mono);font-size:11.5px;line-height:1.35;overflow-wrap:anywhere}
@media (max-width:640px){.psp-query-strip-grid{grid-template-columns:1fr;row-gap:5px}.psp-query-strip-row{display:block}.psp-query-strip-source{justify-self:start;margin-top:3px}.psp-query-strip-chips{margin-top:5px}}
</style>
<script data-psp-query-strip-compat>
(function(){
  var SOURCE_LABELS={
    "vpnsci-search-session":"seed","vpnsci_seed":"seed","seed":"seed",
    "openalex":"OpenAlex","semantic_scholar":"Semantic Scholar",
    "semanticscholar":"Semantic Scholar","s2":"Semantic Scholar",
    "crossref":"CrossRef","pubmed":"PubMed","arxiv":"arXiv"
  };
  function labelFor(source){
    var raw=String(source||"").trim();
    return SOURCE_LABELS[raw.toLowerCase()]||raw;
  }
  function userQuery(metadata,queryDisplay){
    return String(
      (queryDisplay&&queryDisplay.user_query)||
      metadata.display_query||
      metadata.user_query||
      metadata.query||
      ""
    ).trim();
  }
  function collectGroups(){
    var report=window.__REPORT_DATA__||{};
    var metadata=report.metadata||report.reportMeta||{};
    var queryDisplay=metadata.query_display||{};
    var raw=queryDisplay.actual_queries||metadata.actual_queries||[];
    var user=userQuery(metadata,queryDisplay);
    var groups=[];
    if(!Array.isArray(raw)) return groups;
    raw.forEach(function(group){
      if(!group) return;
      var source=labelFor(group.source);
      var seen={};
      var queries=[];
      (Array.isArray(group.queries)?group.queries:[]).forEach(function(query){
        var text=String(query||"").trim();
        if(!text) return;
        if(source==="seed"&&user&&text===user) return;
        if(seen[text]) return;
        seen[text]=true;
        queries.push(text);
      });
      if(source&&queries.length) groups.push({source:source,queries:queries});
    });
    return groups;
  }
  function stripLabel(){
    return window.__REPORT_LANG__==="zh"?"实际检索 query":"Actual search queries";
  }
  function makeStrip(groups){
    var root=document.createElement("div");
    root.className="psp-query-strip";
    root.setAttribute("aria-label",stripLabel());
    var kicker=document.createElement("div");
    kicker.className="psp-query-strip-kicker";
    kicker.textContent=stripLabel();
    root.appendChild(kicker);
    var grid=document.createElement("div");
    grid.className="psp-query-strip-grid";
    groups.forEach(function(group){
      var row=document.createElement("div");
      row.className="psp-query-strip-row";
      var source=document.createElement("span");
      source.className="psp-query-strip-source";
      source.textContent=group.source;
      var chips=document.createElement("span");
      chips.className="psp-query-strip-chips";
      group.queries.forEach(function(query){
        var chip=document.createElement("span");
        chip.className="psp-query-strip-chip";
        chip.textContent=query;
        chips.appendChild(chip);
      });
      row.appendChild(source);
      row.appendChild(chips);
      grid.appendChild(row);
    });
    root.appendChild(grid);
    return root;
  }
  function findHeroTitle(){
    return document.querySelector(".rd-hero-swiss h1,.rd-hero-editorial h1,.rd-hero-document h1,header h1");
  }
  function apply(){
    if(document.querySelector(".psp-query-strip")) return true;
    var groups=collectGroups();
    if(!groups.length) return false;
    var h1=findHeroTitle();
    if(!h1||!h1.parentNode) return false;
    h1.insertAdjacentElement("afterend",makeStrip(groups));
    return true;
  }
  function boot(){
    if(apply()) return;
    var tries=0;
    var timer=setInterval(function(){
      tries+=1;
      if(apply()||tries>100) clearInterval(timer);
    },100);
    if(document.body&&window.MutationObserver){
      var observer=new MutationObserver(function(){
        if(apply()){
          observer.disconnect();
          clearInterval(timer);
        }
      });
      observer.observe(document.body,{childList:true,subtree:true});
      setTimeout(function(){observer.disconnect();},10000);
    }
  }
  if(document.readyState==="loading"){
    document.addEventListener("DOMContentLoaded",boot);
  }else{
    boot();
  }
})();
</script>'''
    if "</body>" in bundle_html:
        return bundle_html.replace("</body>", f"{injection}</body>", 1)
    return bundle_html + injection


def _resolve_language(
    explicit: Optional[str],
    metadata: Dict[str, Any],
) -> str:
    """Pick "en" or "zh" from explicit arg, metadata, or default "en".

    Anything other than "en"/"zh" falls back to "en" with a stderr warning.
    The React bundle's `installLanguage()` does an identical fallback, so
    even a corrupted value can't crash rendering — but logging here lets a
    main agent see something is up.
    """
    candidate = explicit or (
        metadata.get("language") if isinstance(metadata, dict) else None
    )
    if candidate in ("en", "zh"):
        return candidate
    if candidate:
        log.warning(
            "Unknown language %r; falling back to 'en'. Acceptable values: en, zh.",
            candidate,
        )
    return "en"


def _inject_language(bundle_html: str, language: str) -> str:
    """Insert `<script>window.__REPORT_LANG__ = "..."</script>` before the first <script>.

    Placed BEFORE `__REPORT_DATA__` so that `installLanguage()` runs first
    inside the React bundle and `window.S` is set before any component reads
    a translation. The bundle's i18n.ts uses the same fallback chain (window
    global → "en"), so a missing injection here is safe — but the explicit
    injection makes the active language visible in the HTML source.
    """
    safe_lang = "zh" if language == "zh" else "en"
    injection = f'<script>window.__REPORT_LANG__ = "{safe_lang}";</script>'

    match = _FIRST_SCRIPT_RE.search(bundle_html)
    if not match:
        if "</body>" in bundle_html:
            return bundle_html.replace("</body>", f"{injection}</body>", 1)
        return bundle_html + injection
    insert_at = match.start()
    return bundle_html[:insert_at] + injection + bundle_html[insert_at:]


# ---------------------------------------------------------------------------
# Size policy
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> Any:
    if not path.exists():
        raise HtmlRenderError(f"Required input not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_optional_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    import sys
    import tempfile

    parser = argparse.ArgumentParser(
        description=(
            "Render the HTML report (Shadcn webartifacts path) by hydrating "
            "the pre-built React bundle with materialized JSON data."
        )
    )
    parser.add_argument(
        "--data",
        type=Path,
        help="Path to report_data.json (consolidated bundle).",
    )
    parser.add_argument(
        "--materialized-dir",
        type=Path,
        help="Directory with chart_data/paper_list/metadata/prisma_log JSON siblings.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Where to write report.html.",
    )
    parser.add_argument(
        "--query",
        default="",
        help="Optional original user query (fallback when metadata lacks it).",
    )
    parser.add_argument(
        "--language",
        choices=("en", "zh"),
        default=None,
        help=(
            "UI language for the rendered report. The bundle ships with both "
            "English and Chinese dictionaries; this flag controls which one "
            "mounts. Resolution order: explicit flag > metadata.language > 'en'. "
            "Set this based on the user's query language: CJK characters → zh, "
            "otherwise → en. (Paper data — titles, authors, abstracts — is "
            "never translated; only the report's UI chrome.)"
        ),
    )
    args = parser.parse_args()

    if args.materialized_dir:
        materialized_dir = args.materialized_dir
    elif args.data and args.data.exists():
        payload = json.loads(args.data.read_text(encoding="utf-8"))
        tmp_dir = Path(tempfile.mkdtemp(prefix="html_webart_"))
        (tmp_dir / "chart_data.json").write_text(
            json.dumps(payload.get("chart_data", {}), ensure_ascii=False), encoding="utf-8"
        )
        (tmp_dir / "paper_list.json").write_text(
            json.dumps(payload.get("paper_list", []), ensure_ascii=False), encoding="utf-8"
        )
        (tmp_dir / "metadata.json").write_text(
            json.dumps(payload.get("metadata", {}), ensure_ascii=False), encoding="utf-8"
        )
        (tmp_dir / "prisma_log.json").write_text(
            json.dumps(payload.get("prisma_log", {}), ensure_ascii=False), encoding="utf-8"
        )
        materialized_dir = tmp_dir
    else:
        sys.exit(
            "html_renderer_webartifacts: provide --data report_data.json or "
            "--materialized-dir"
        )

    out = render_html_webartifacts(
        materialized_data_dir=materialized_dir,
        output_path=args.output,
        user_query=args.query,
        language=args.language,
    )
    print(f"html_renderer_webartifacts: wrote {out}")
