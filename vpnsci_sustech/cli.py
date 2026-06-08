"""CLI interface for vpnsci-sustech."""

import json
import logging
import os
import sys
from pathlib import Path

# Fix Windows console encoding for Unicode output
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import typer
from rich.console import Console
from rich.table import Table

from . import report_bridge, report_tools
from .config import Config
from .fetcher import PaperFetcher
from .file_naming import POLICIES, build_artifact_stem, reserve_unique_path
from .models import Paper
from .report_recovery import resolve_report_recovery_session
from .schools import get_school, list_schools, search_schools
from .sources import backend_routing, cnki, publisher_search, search_mode, semantic_scholar, standard_search
from .sources.search_cache import load_session, save_session

app = typer.Typer(
    name="vpnsci-sustech",
    help="Fetch academic papers via WebVPN, Open Access, or arXiv.",
    no_args_is_help=True,
)
report_tools_app = typer.Typer(help="Install and configure bundled professional report tools.")
app.add_typer(report_tools_app, name="report-tools")
console = Console()


def _load_cnki_batch_items(file: Path) -> list[cnki.CNKIBatchItem]:
    """Load CNKI batch items from JSON, JSONL, or plain URL lines."""

    text = file.read_text(encoding="utf-8-sig")
    stripped = text.strip()
    if not stripped:
        return []
    records = []
    if stripped.startswith("["):
        loaded = json.loads(stripped)
        records = loaded if isinstance(loaded, list) else []
    elif stripped.startswith("{") and "\n" not in stripped:
        loaded = json.loads(stripped)
        if isinstance(loaded, dict) and isinstance(loaded.get("items"), list):
            records = loaded["items"]
        else:
            records = [loaded]
    else:
        for line in text.splitlines():
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            if value.startswith("{"):
                records.append(json.loads(value))
            else:
                records.append({"detail_url": value})

    items: list[cnki.CNKIBatchItem] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        detail_url = str(record.get("detail_url") or record.get("url") or "").strip()
        if not detail_url:
            continue
        items.append(
            cnki.CNKIBatchItem(
                detail_url=detail_url,
                title=str(record.get("title") or ""),
                first_author=str(record.get("first_author") or record.get("firstAuthor") or ""),
                cnki_id=str(record.get("cnki_id") or record.get("cnkiId") or ""),
                source_url=str(record.get("source_url") or record.get("sourceUrl") or detail_url),
            )
        )
    return items


def _reserve_result_output_path(config: Config, paper: Paper, identifier: str, ext: str, *, filename_policy: str = "", filename_template: str = "") -> Path:
    """Reserve a result sidecar path using the same filename policy family as artifacts."""

    policy = filename_policy or getattr(config, "paper_filename_policy", "identifier") or "identifier"
    template = filename_template or getattr(config, "paper_filename_template", "") or ""
    max_length = int(getattr(config, "paper_filename_max_length", 180) or 180)
    collision = getattr(config, "paper_filename_collision", "hash") or "hash"
    stem = build_artifact_stem(
        paper,
        policy=policy,
        template=template,
        max_length=max_length,
    )
    return reserve_unique_path(
        config.output_dir,
        stem=stem,
        ext=ext,
        collision_key=paper.doi or paper.url or identifier or stem,
        collision=collision,
        overwrite=False,
    )


def _setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _ensure_email(config: Config):
    """Prompt user to set email if not configured (needed for Unpaywall)."""
    if not config.email:
        console.print("[yellow]Email not configured (needed for Unpaywall OA detection).[/yellow]")
        email = typer.prompt("Enter your email address")
        config.email = email
        config.save()
        console.print(f"[green]Email saved: {email}[/green]")


@app.command()
def login(
    force: bool = typer.Option(False, "--force", "-f", help="Force re-login even if session is valid."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging."),
):
    """Initialize or refresh WebVPN session."""
    _setup_logging(verbose)
    config = Config.load()
    fetcher = PaperFetcher(config)

    console.print("[bold]Checking WebVPN session...[/bold]")
    if fetcher.auth.login(force=force):
        console.print("[green]WebVPN session is active.[/green]")
    else:
        console.print("[red]Failed to authenticate with WebVPN.[/red]")
        raise typer.Exit(1)


@app.command()
def fetch(
    identifier: str = typer.Argument(help="DOI or URL of the paper to fetch."),
    output: str = typer.Option("", "--output", "-o", help="Output directory for PDFs."),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json, markdown, text."),
    text_only: bool = typer.Option(False, "--text-only", "-t", help="Output only plain text (minimal tokens)."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass cache."),
    filename_policy: str = typer.Option("", "--filename-policy", help="Filename policy: identifier, title_author, title_year_author, custom."),
    filename_template: str = typer.Option("", "--filename-template", help="Filename template for custom policy."),
    ask_rename: bool = typer.Option(False, "--ask-rename", help="Prompt once for this fetch's filename policy."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging."),
):
    """Fetch a single paper by DOI or URL."""
    _setup_logging(verbose)
    config = Config.load()
    _ensure_email(config)
    if output:
        config.output_dir = output

    fetcher = PaperFetcher(config)
    try:
        console.print(f"[bold]Fetching:[/bold] {identifier}")
        effective_policy = filename_policy
        if ask_rename and not effective_policy:
            effective_policy = typer.prompt(
                "Filename policy",
                default=config.paper_filename_policy,
            )
        paper = fetcher.fetch(
            identifier,
            use_cache=not no_cache,
            filename_policy=effective_policy,
            filename_template=filename_template,
        )

        if not paper.full_text and not paper.abstract:
            console.print("[yellow]Warning: Could not extract full text.[/yellow]")

        if text_only:
            console.print(paper.to_text())
        elif format == "markdown":
            console.print(paper.to_markdown())
        elif format == "text":
            console.print(paper.to_text())
        else:
            console.print(paper.to_json())

        if paper.pdf_path:
            console.print(f"\n[dim]PDF saved to: {paper.pdf_path}[/dim]")
        console.print(f"[dim]Source: {paper.source}[/dim]")

    finally:
        fetcher.close()


@app.command("fetch-hit")
def fetch_hit(
    search_session_id: str = typer.Argument(help="Search session id."),
    hit_key: str = typer.Argument(help="Persisted SearchHit hit_key."),
    filename_policy: str = typer.Option("", "--filename-policy", help="Filename policy override."),
    filename_template: str = typer.Option("", "--filename-template", help="Filename template override."),
    confirm_live_access: bool = typer.Option(False, "--confirm-live-access", help="Required for CNKI live continuation."),
):
    """Fetch full text from a saved SearchSession hit."""
    cfg = Config.load()
    session = load_session(search_session_id, Path(cfg.cache_dir))
    hit = next((item for item in session.hits if item.hit_key == hit_key), None)
    if hit is None:
        console.print(f"[red]Hit not found: {hit_key}[/red]")
        raise typer.Exit(1)
    fetcher = PaperFetcher(cfg)
    try:
        paper = fetcher.fetch_from_search_hit(
            hit,
            filename_policy=filename_policy,
            filename_template=filename_template,
            confirm_live_access=confirm_live_access,
        )
        console.print(paper.to_markdown(include_pdf_path=True))
    finally:
        fetcher.close()


@app.command()
def batch(
    file: Path = typer.Argument(help="File containing DOIs (one per line)."),
    output: str = typer.Option("", "--output", "-o", help="Output directory."),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json, markdown, text."),
    filename_policy: str = typer.Option("", "--filename-policy", help="Filename policy: identifier, title_author, title_year_author, custom."),
    filename_template: str = typer.Option("", "--filename-template", help="Filename template for custom policy."),
    ask_rename: bool = typer.Option(False, "--ask-rename", help="Prompt once for this batch's filename policy."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging."),
):
    """Fetch multiple papers from a file of DOIs."""
    _setup_logging(verbose)

    if not file.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1)

    dois = [
        line.strip()
        for line in file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    if not dois:
        console.print("[yellow]No DOIs found in file.[/yellow]")
        raise typer.Exit(0)

    console.print(f"[bold]Found {len(dois)} DOIs to fetch.[/bold]")

    config = Config.load()
    if output:
        config.output_dir = output

    fetcher = PaperFetcher(config)
    results_dir = Path(config.output_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    effective_policy = filename_policy
    if ask_rename and not effective_policy:
        effective_policy = typer.prompt(
            "Filename policy",
            default=config.paper_filename_policy,
        )

    succeeded = 0
    failed = 0

    try:
        for i, doi in enumerate(dois, 1):
            console.print(f"\n[bold][{i}/{len(dois)}][/bold] Fetching: {doi}")
            try:
                paper = fetcher.fetch(
                    doi,
                    filename_policy=effective_policy,
                    filename_template=filename_template,
                )
                if paper.full_text:
                    succeeded += 1
                    # Save result
                    if format == "markdown":
                        out_file = _reserve_result_output_path(
                            config,
                            paper,
                            doi,
                            "md",
                            filename_policy=effective_policy,
                            filename_template=filename_template,
                        )
                        out_file.write_text(paper.to_markdown(), encoding="utf-8")
                    elif format == "text":
                        out_file = _reserve_result_output_path(
                            config,
                            paper,
                            doi,
                            "txt",
                            filename_policy=effective_policy,
                            filename_template=filename_template,
                        )
                        out_file.write_text(paper.to_text(), encoding="utf-8")
                    else:
                        out_file = _reserve_result_output_path(
                            config,
                            paper,
                            doi,
                            "json",
                            filename_policy=effective_policy,
                            filename_template=filename_template,
                        )
                        out_file.write_text(paper.to_json(), encoding="utf-8")
                    console.print(f"  [green]OK[/green] → {out_file.name}")
                else:
                    failed += 1
                    console.print("  [yellow]No full text extracted[/yellow]")
            except Exception as e:
                failed += 1
                console.print(f"  [red]Error: {e}[/red]")

        console.print(f"\n[bold]Done:[/bold] {succeeded} succeeded, {failed} failed out of {len(dois)}.")

    finally:
        fetcher.close()


@app.command()
def search(
    query: str = typer.Argument(help="Search query."),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum results."),
    year: str = typer.Option("", "--year", "-y", help="Year range, e.g., '2020-2024' or '2020-'."),
    backend: str = typer.Option("", "--backend", help="Optional publisher-native backend: sciencedirect, springerlink, wiley, ieee."),
    do_fetch: bool = typer.Option(False, "--fetch", help="Also fetch full text for results with DOIs."),
    filename_policy: str = typer.Option("", "--filename-policy", help="Filename policy for --fetch downloads."),
    filename_template: str = typer.Option("", "--filename-template", help="Filename template for --fetch downloads."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging."),
):
    """Search for papers."""
    _setup_logging(verbose)

    console.print(f"[bold]Searching:[/bold] {query}")
    config = Config.load()
    route = backend_routing.resolve_requested_backend(query, explicit_backend=backend)
    if route.backend == "cnki":
        console.print("[yellow]CNKI backend is experimental and currently gated at the session/DOM probe stage.[/yellow]")
        session = cnki.search_cnki(query, limit=limit, config=config)
        console.print(f"[dim]Search Session: {session.session_id}[/dim]")
        if session.source_summary:
            console.print(f"[dim]Source Summary: {session.source_summary}[/dim]")
        for err in session.errors:
            console.print(f"[yellow]{err.source} {err.code}: {err.message}[/yellow]")
        console.print("[yellow]No CNKI network access or download was attempted.[/yellow]")
        console.print("[yellow]Use cnki-search-html with captured page source, or cnki-smoke after explicit confirmation.[/yellow]")
        raise typer.Exit(0)
    if route.backend:
        results = publisher_search.search(query, backend=route.backend, limit=limit)
    else:
        mode_decision = search_mode.classify_search_mode(query, {})
        session = standard_search.search(
            query,
            limit=limit,
            year_range=year or None,
            config=config,
        )
        results = session.hits
        console.print(f"[dim]Search Session: {session.session_id}[/dim]")
        if session.source_summary:
            console.print(f"[dim]Source Summary: {session.source_summary}[/dim]")
        if session.errors:
            for err in session.errors:
                console.print(f"[yellow]{err.source} {err.code}: {err.message}[/yellow]")
        if mode_decision.mode == "pro":
            console.print("[cyan]检测到专业调研强触发，标准检索会话已作为报告种子保存。[/cyan]")
            try:
                report_result = report_bridge.start_report_from_session(session.session_id, config=config, mode="full", display_query=query, language="zh" if any("\u4e00" <= ch <= "\u9fff" for ch in query) else "en", open_report=True)
            except report_bridge.ReportBridgeConfigError as e:
                console.print(f"[yellow]报告桥接尚未配置：{e}[/yellow]")
                console.print("[yellow]将继续显示标准检索结果。[/yellow]")
            except report_bridge.ReportBridgeError as e:
                console.print(f"[red]报告生成失败：{e}[/red]")
                console.print("[yellow]将继续显示标准检索结果。[/yellow]")
            else:
                if getattr(report_result, "status", "") == "handoff_required":
                    console.print("[yellow]完整专业调研需要 handoff，当前未启动 HTML 生成。[/yellow]")
                    console.print(f"Handoff: {report_result.handoff_path}")
                    console.print("Automation: Codex 会话层读取 handoff 后继续跑 full workflow。")
                    console.print("Multi-agent: 需要 multi_agent_v1.spawn_agent；SubAgent 失败必须在对话内汇报，不会静默退回 seed_preview。")
                    console.print("[yellow]将继续显示标准检索结果。[/yellow]")
                else:
                    console.print("[green]专业调研报告已生成。[/green]")
                    console.print(f"Report: {report_result.report_path}")
                    return

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        raise typer.Exit(0)

    # Display results in a table
    table = Table(title=f"Search Results ({len(results)})")
    table.add_column("#", style="dim", width=3)
    table.add_column("Year", width=5)
    table.add_column("Title", max_width=60)
    table.add_column("Authors", max_width=30)
    table.add_column("DOI", max_width=25)
    table.add_column("Cites", width=5, justify="right")

    for i, r in enumerate(results, 1):
        authors_str = ", ".join(r.authors[:3])
        if len(r.authors) > 3:
            authors_str += " et al."
        table.add_row(
            str(i),
            str(r.year or ""),
            r.title[:60],
            authors_str[:30],
            r.doi[:25] if r.doi else r.arxiv_id[:25] if getattr(r, "arxiv_id", "") else "",
            str(getattr(r, "citation_count", 0)),
        )

    console.print(table)

    if not backend and "session" in locals() and session.upgrade_suggested:
        console.print(
            "[cyan]如果你想要更全面覆盖、去重整合和 HTML 综合报告，"
            "我可以基于这次检索继续进入“专业调研”模式。[/cyan]"
        )

    # Optionally fetch full texts
    if do_fetch:
        fetchable = [r for r in results if r.doi or r.arxiv_id]
        if fetchable:
            console.print(f"\n[bold]Fetching {len(fetchable)} papers...[/bold]")
            config = Config.load()
            fetcher = PaperFetcher(config)
            try:
                for r in fetchable:
                    identifier = r.doi or f"arxiv:{r.arxiv_id}"
                    console.print(f"  Fetching: {identifier}")
                    try:
                        paper = fetcher.fetch(
                            identifier,
                            filename_policy=filename_policy,
                            filename_template=filename_template,
                        )
                        status = "[green]OK[/green]" if paper.full_text else "[yellow]No text[/yellow]"
                        console.print(f"    {status}")
                    except Exception as e:
                        console.print(f"    [red]Error: {e}[/red]")
            finally:
                fetcher.close()


@app.command()
def report(
    search_session_id: str = typer.Argument(help="Search session id returned by search."),
    mode: str = typer.Option("full", "--mode", help="Report mode: full or seed_preview."),
):
    """Generate an HTML report from a saved search session."""
    cfg = Config.load()
    try:
        result = report_bridge.start_report_from_session(search_session_id, config=cfg, mode=mode, open_report=True)
    except report_bridge.ReportBridgeConfigError as e:
        console.print(f"[yellow]报告桥接尚未配置：{e}[/yellow]")
        raise typer.Exit(1)
    except report_bridge.ReportBridgeError as e:
        console.print(f"[red]报告生成失败：{e}[/red]")
        raise typer.Exit(1)

    if getattr(result, "status", "") == "handoff_required":
        console.print("[yellow]完整专业调研需要 handoff，当前未启动 HTML 生成。[/yellow]")
        console.print(f"Handoff: {result.handoff_path}")
        console.print("Automation: Codex 会话层读取 handoff 后继续跑 full workflow。")
        console.print("Multi-agent: 需要 multi_agent_v1.spawn_agent；SubAgent 失败必须在对话内汇报，不会静默退回 seed_preview。")
    elif getattr(result, "status", "") == "theme_postprocess_required":
        console.print("[yellow]主题后处理需要 host Agent 接管，当前未启动最终 HTML 渲染。[/yellow]")
        console.print(f"Materialized Dir: {result.materialized_dir}")
        console.print(f"Request: {result.theme_postprocess_request_path}")
        console.print(f"Result Target: {result.theme_postprocess_result_path}")
        console.print("Automation: host Agent 读取 request，写回 result，再回到正式主链完成渲染。")
    else:
        console.print("[green]专业调研报告已生成。[/green]")
        console.print(f"Local Path: {result.report_path}")
        console.print("Tip: 如果文件在 Agent 代码编辑器内打开，可右键 HTML 文件标签，选择“在资源管理器中显示/打开”，再用浏览器打开原文件。")
    console.print(f"Seed Session: {result.seed_session_id}")
    console.print(f"Deduped Papers: {result.deduped_paper_count}")


@app.command("report-recover")
def report_recover(
    sidecar: str = typer.Option("", "--sidecar", help="Download workflow sidecar JSON path."),
    report_json: str = typer.Option("", "--report-json", help="Legacy materialized report JSON path."),
    mode: str = typer.Option("seed_preview", "--mode", help="Report mode: full or seed_preview."),
    prefer: str = typer.Option("auto", "--prefer", help="Recovery preference: auto/A/B/C."),
):
    """Recover a SearchSession from sidecar/legacy materials and start report generation."""
    if not sidecar and not report_json:
        console.print("[red]Missing recovery input: provide --sidecar or --report-json.[/red]")
        raise typer.Exit(1)
    cfg = Config.load()
    resolved = resolve_report_recovery_session(
        sidecar=sidecar or None,
        report_json=report_json or None,
        prefer=prefer,
    )
    session = resolved.session
    save_session(session, Path(cfg.cache_dir))
    result = report_bridge.start_report_from_session(
        session.session_id,
        config=cfg,
        mode=mode,
        display_query=session.display_query or session.recovered_label,
        open_report=True,
    )
    console.print(f"Recovery Kind: {resolved.decision.recovery_kind}")
    console.print(f"Restored Session: {session.session_id}")
    console.print(f"Display Query: {session.display_query or session.recovered_label}")
    console.print(f"Report Status: {result.status}")
    console.print(f"Seed Session: {result.seed_session_id}")


@report_tools_app.command("install")
def install_report_tools(
    force: bool = typer.Option(False, "--force", help="Replace existing local paper-search-pro runtime copy."),
):
    """Install bundled paper-search-pro snapshot into the user-local runtime directory."""
    cfg = report_tools.ensure_report_tool_configured(Config.load(), force=force)
    result = report_tools.install_report_tool(cfg, force=False)
    console.print("[green]paper-search-pro report tool configured.[/green]")
    console.print(f"Bundled snapshot: {result.bundled_root}")
    console.print(f"Local runtime:    {result.local_root}")
    console.print(f"Report output:    {result.output_dir}")
    console.print(f"Command:          {result.command}")
    console.print(f"OpenAlex key:     {'SET' if result.openalex_configured else 'EMPTY'}")
    console.print(f"S2 key:           {'SET' if result.semantic_scholar_configured else 'EMPTY'}")


@app.command()
def cache(
    action: str = typer.Argument(help="Action: 'clear' to remove cached results."),
):
    """Manage the paper cache."""
    if action == "clear":
        config = Config.load()
        fetcher = PaperFetcher(config)
        fetcher.clear_cache()
        console.print("[green]Cache cleared.[/green]")
    else:
        console.print(f"[red]Unknown action: {action}. Use 'clear'.[/red]")
        raise typer.Exit(1)


@app.command()
def schools(
    query: str = typer.Argument("", help="Search query (name, province, or host). Omit to list all."),
):
    """List or search supported universities."""
    if query:
        results = search_schools(query)
    else:
        results = list_schools()

    if not results:
        console.print(f"[yellow]No schools found matching '{query}'.[/yellow]")
        raise typer.Exit(0)

    table = Table(title=f"Supported Schools ({len(results)})")
    table.add_column("#", style="dim", width=4)
    table.add_column("Province", width=10)
    table.add_column("School", max_width=25)
    table.add_column("Type", width=12)
    table.add_column("Host", max_width=40)
    table.add_column("Custom Key", width=5, justify="center")

    from .schools import WEBVPN_DEFAULT_KEY
    for i, s in enumerate(results, 1):
        has_custom = "Y" if s.key != WEBVPN_DEFAULT_KEY else ""
        type_label = "EasyConnect" if s.school_type == "easyconnect" else "WebVPN"
        table.add_row(str(i), s.province, s.name, type_label, s.host, has_custom)

    console.print(table)


@app.command()
def config_cmd(
    show: bool = typer.Option(True, "--show", help="Show current config."),
    set_email: str = typer.Option("", "--email", help="Set email for Unpaywall API."),
    set_output: str = typer.Option("", "--output-dir", help="Set default output directory."),
    set_webvpn_url: str = typer.Option("", "--webvpn-url", help="Set WebVPN base URL."),
    set_school: str = typer.Option("", "--school", help="Set school (use 'vpnsci-sustech schools' to list)."),
    set_proxy_url: str = typer.Option("", "--proxy-url", help="Set SOCKS5 proxy URL for EasyConnect."),
    set_elsevier_key: str = typer.Option("", "--elsevier-api-key", help="Set Elsevier API key."),
    set_elsevier_token: str = typer.Option("", "--elsevier-inst-token", help="Set Elsevier institutional token."),
    set_s2_key: str = typer.Option("", "--semantic-scholar-api-key", help="Set Semantic Scholar API key."),
    set_openalex_key: str = typer.Option("", "--openalex-api-key", help="Set OpenAlex API key."),
    set_paper_search_pro_root: str = typer.Option("", "--paper-search-pro-root", help="Set paper-search-pro root path."),
    set_paper_search_pro_command: str = typer.Option("", "--paper-search-pro-command", help="Set paper-search-pro command template."),
    set_paper_search_pro_output_dir: str = typer.Option("", "--paper-search-pro-output-dir", help="Set report output directory."),
    install_report_tools_flag: bool = typer.Option(False, "--install-report-tools", help="Install bundled paper-search-pro into the user-local runtime directory."),
    set_flaresolverr: str = typer.Option("", "--flaresolverr-url", help="Set FlareSolverr URL."),
    set_carsi_enable: bool = typer.Option(False, "--carsi-enable", help="Enable CARSI/Shibboleth federated auth."),
    set_carsi_disable: bool = typer.Option(False, "--carsi-disable", help="Disable CARSI auth."),
    set_carsi_school: str = typer.Option("", "--carsi-school", help="Set school name for CARSI WAYF."),
    set_paper_filename_policy: str = typer.Option("", "--paper-filename-policy", help="Set default paper filename policy."),
    set_paper_filename_template: str = typer.Option("", "--paper-filename-template", help="Set default paper filename template."),
    set_paper_filename_ask: str = typer.Option("", "--paper-filename-ask", help="Set MCP filename ask default: true or false."),
    set_paper_filename_max_length: int | None = typer.Option(None, "--paper-filename-max-length", help="Set max filename stem length."),
    set_paper_filename_collision: str = typer.Option("", "--paper-filename-collision", help="Set filename collision strategy: hash or increment."),
    set_cnki_convert_caj_to_pdf: str = typer.Option("", "--cnki-convert-caj-to-pdf", help="Enable optional external CNKI CAJ conversion: true or false."),
    set_cnki_caj_converter_command: str = typer.Option("", "--cnki-caj-converter-command", help="External CAJ converter command template with {input} and {output}."),
):
    """View or update configuration."""
    cfg = Config.load()
    changed = False

    if set_email:
        cfg.email = set_email
        changed = True
        console.print(f"[green]Email set to: {set_email}[/green]")

    if set_output:
        cfg.output_dir = set_output
        changed = True
        console.print(f"[green]Output dir set to: {set_output}[/green]")

    if set_webvpn_url:
        cfg.webvpn_base_url = set_webvpn_url.rstrip("/")
        changed = True
        console.print(f"[green]WebVPN base URL set to: {set_webvpn_url}[/green]")

    if set_school:
        try:
            entry = get_school(set_school)
            cfg.school = entry.name
            cfg.webvpn_base_url = entry.host
            changed = True
            type_label = "EasyConnect" if entry.school_type == "easyconnect" else "WebVPN"
            console.print(f"[green]School set to: {entry.name} ({type_label}, {entry.host})[/green]")
            if entry.school_type == "easyconnect":
                console.print("[yellow]This school uses EasyConnect. Please:[/yellow]")
                console.print("  1. Connect via zju-connect: [cyan]zju-connect -server {0}[/cyan]".format(entry.host))
                console.print("  2. Set proxy: [cyan]vpnsci-sustech config-cmd --proxy-url socks5://127.0.0.1:1080[/cyan]")
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)

    if set_proxy_url:
        cfg.proxy_url = set_proxy_url
        changed = True
        console.print(f"[green]Proxy URL set to: {set_proxy_url}[/green]")

    if set_elsevier_key:
        cfg.elsevier_api_key = set_elsevier_key
        changed = True
        console.print("[green]Elsevier API key saved.[/green]")

    if set_elsevier_token:
        cfg.elsevier_inst_token = set_elsevier_token
        changed = True
        console.print("[green]Elsevier institutional token saved.[/green]")

    if set_s2_key:
        cfg.semantic_scholar_api_key = set_s2_key
        changed = True
        console.print("[green]Semantic Scholar API key saved.[/green]")

    if set_openalex_key:
        cfg.openalex_api_key = set_openalex_key
        changed = True
        console.print("[green]OpenAlex API key saved.[/green]")

    if set_paper_search_pro_root:
        cfg.paper_search_pro_root = set_paper_search_pro_root
        changed = True
        console.print(f"[green]paper-search-pro root set to: {set_paper_search_pro_root}[/green]")

    if set_paper_search_pro_command:
        cfg.paper_search_pro_command = set_paper_search_pro_command
        changed = True
        console.print("[green]paper-search-pro command saved.[/green]")

    if set_paper_search_pro_output_dir:
        cfg.paper_search_pro_output_dir = set_paper_search_pro_output_dir
        changed = True
        console.print(f"[green]paper-search-pro output dir set to: {set_paper_search_pro_output_dir}[/green]")

    if install_report_tools_flag:
        cfg = report_tools.ensure_report_tool_configured(cfg, force=False)
        changed = False
        console.print("[green]paper-search-pro report tool installed and configured.[/green]")

    if set_flaresolverr:
        cfg.flaresolverr_url = set_flaresolverr.rstrip("/")
        changed = True
        console.print(f"[green]FlareSolverr URL set to: {set_flaresolverr}[/green]")

    if set_carsi_enable:
        cfg.carsi_enabled = True
        changed = True
        console.print("[green]CARSI/Shibboleth federated auth enabled.[/green]")

    if set_carsi_disable:
        cfg.carsi_enabled = False
        changed = True
        console.print("[yellow]CARSI auth disabled.[/yellow]")

    if set_carsi_school:
        cfg.carsi_idp_name = set_carsi_school
        changed = True
        console.print(f"[green]CARSI school set to: {set_carsi_school}[/green]")

    if set_paper_filename_policy:
        normalized_policy = set_paper_filename_policy.strip().lower()
        if normalized_policy not in POLICIES:
            console.print("[red]Paper filename policy must be one of: identifier, title_author, title_year_author, custom.[/red]")
            raise typer.Exit(1)
        cfg.paper_filename_policy = normalized_policy
        changed = True
        console.print(f"[green]Paper filename policy set to: {normalized_policy}[/green]")

    if set_paper_filename_template:
        cfg.paper_filename_template = set_paper_filename_template
        changed = True
        console.print("[green]Paper filename template saved.[/green]")

    if set_paper_filename_ask:
        cfg.paper_filename_ask = set_paper_filename_ask.strip().lower() in {"1", "true", "yes", "y", "on"}
        changed = True
        console.print(f"[green]Paper filename ask set to: {cfg.paper_filename_ask}[/green]")

    if set_paper_filename_max_length is not None:
        if set_paper_filename_max_length <= 0:
            console.print("[red]Paper filename max length must be a positive integer.[/red]")
            raise typer.Exit(1)
        cfg.paper_filename_max_length = set_paper_filename_max_length
        changed = True
        console.print(f"[green]Paper filename max length set to: {set_paper_filename_max_length}[/green]")

    if set_paper_filename_collision:
        normalized_collision = set_paper_filename_collision.strip().lower()
        if normalized_collision not in {"hash", "increment"}:
            console.print("[red]Paper filename collision must be hash or increment.[/red]")
            raise typer.Exit(1)
        cfg.paper_filename_collision = normalized_collision
        changed = True
        console.print(f"[green]Paper filename collision set to: {normalized_collision}[/green]")

    if set_cnki_convert_caj_to_pdf:
        cfg.cnki_convert_caj_to_pdf = set_cnki_convert_caj_to_pdf.strip().lower() in {"1", "true", "yes", "y", "on"}
        changed = True
        console.print(f"[green]CNKI CAJ conversion set to: {cfg.cnki_convert_caj_to_pdf}[/green]")

    if set_cnki_caj_converter_command:
        cfg.cnki_caj_converter_command = set_cnki_caj_converter_command
        changed = True
        console.print("[green]CNKI CAJ converter command saved.[/green]")

    if changed:
        cfg.save()

    has_setter = any([set_email, set_output, set_webvpn_url, set_school, set_proxy_url,
                      set_elsevier_key, set_elsevier_token, set_s2_key, set_flaresolverr,
                      set_openalex_key, set_paper_search_pro_root, set_paper_search_pro_command,
                      set_paper_search_pro_output_dir, install_report_tools_flag,
                      set_carsi_enable, set_carsi_disable, set_carsi_school,
                      set_paper_filename_policy, set_paper_filename_template, set_paper_filename_ask,
                      set_paper_filename_max_length is not None, set_paper_filename_collision,
                      set_cnki_convert_caj_to_pdf, set_cnki_caj_converter_command])
    if show and not has_setter:
        # Determine school type
        try:
            from .schools import get_school as _get_school
            school_entry = _get_school(cfg.school)
            school_type = school_entry.school_type
        except ValueError:
            school_type = "unknown"

        console.print("[bold]Current configuration:[/bold]")
        console.print(f"  School:            {cfg.school} ({school_type})")
        console.print(f"  WebVPN base:       {cfg.webvpn_base_url}")
        console.print(f"  Proxy URL:         {cfg.proxy_url or '(not set)'}")
        console.print(f"  Email:             {cfg.email}")
        console.print(f"  Elsevier API key:  {'****' if cfg.elsevier_api_key else '(not set)'}")
        console.print(f"  Elsevier inst tok: {'****' if cfg.elsevier_inst_token else '(not set)'}")
        console.print(f"  Semantic Scholar:  {'****' if cfg.semantic_scholar_api_key else '(not set)'}")
        console.print(f"  OpenAlex API key:  {'****' if cfg.openalex_api_key else '(not set)'}")
        console.print(f"  paper-search-pro:  {cfg.paper_search_pro_root or '(not set)'}")
        console.print(f"  report command:    {'(set)' if cfg.paper_search_pro_command else '(not set)'}")
        console.print(f"  report output dir: {cfg.paper_search_pro_output_dir or '(not set)'}")
        console.print(f"  FlareSolverr URL:  {cfg.flaresolverr_url}")
        console.print(f"  CARSI enabled:     {'Yes' if cfg.carsi_enabled else 'No'}")
        console.print(f"  CARSI school:      {cfg.carsi_idp_name or '(not set)'}")
        console.print(f"  Filename policy:   {cfg.paper_filename_policy}")
        console.print(f"  Filename template: {cfg.paper_filename_template}")
        console.print(f"  Filename ask:      {'Yes' if cfg.paper_filename_ask else 'No'}")
        console.print(f"  Filename max len:  {cfg.paper_filename_max_length}")
        console.print(f"  Filename collision:{cfg.paper_filename_collision}")
        console.print(f"  CNKI CAJ convert:  {'Yes' if cfg.cnki_convert_caj_to_pdf else 'No'}")
        console.print(f"  CNKI CAJ command:  {'(set)' if cfg.cnki_caj_converter_command else '(not set)'}")
        console.print(f"  Output dir:        {cfg.output_dir}")
        console.print(f"  Cache dir:         {cfg.cache_dir}")
        console.print(f"  Cookie path:       {cfg.cookie_path}")


@app.command()
def cnki_download(
    detail_url: str = typer.Option("", "--detail-url", help="CNKI detail URL for future visible-browser download."),
    local_file: str = typer.Option("", "--local-file", help="Existing local CNKI artifact to materialize."),
    prefer: str = typer.Option("pdf", "--prefer", help="Preferred live download format."),
    title: str = typer.Option("", "--title", help="Paper title used for filename metadata."),
    first_author: str = typer.Option("", "--first-author", help="First author used for filename metadata."),
    cnki_id: str = typer.Option("", "--cnki-id", help="CNKI identifier."),
    source_url: str = typer.Option("", "--source-url", help="Original CNKI source/download URL."),
    filename_policy: str = typer.Option("", "--filename-policy", help="Filename policy: identifier, title_author, title_year_author, custom."),
    filename_template: str = typer.Option("", "--filename-template", help="Filename template for custom policy."),
    output: str = typer.Option("", "--output", "-o", help="Output directory."),
    live: bool = typer.Option(False, "--live", help="Enable gated visible-browser CNKI download."),
    confirm_live_access: bool = typer.Option(False, "--confirm-live-access", help="Required with --live."),
    mode: str = typer.Option("managed", "--mode", help="managed or attach."),
    debug_port: int = typer.Option(9222, "--debug-port", help="Chrome debug port for mode=attach."),
    timeout: int = typer.Option(45, "--timeout", help="Seconds to wait for one CNKI browser download."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging."),
):
    """Materialize a CNKI artifact or run a gated visible-browser download."""
    _setup_logging(verbose)
    cfg = Config.load()
    if output:
        cfg.output_dir = output
    paper = Paper(
        title=title,
        authors=[first_author] if first_author else [],
        source="cnki",
        url=detail_url or source_url,
    )
    setattr(paper, "cnki_id", cnki_id)
    client = cnki.CNKIClient(cfg)

    if not local_file and not live:
        console.print("[yellow]CNKI live browser download requires --live and --confirm-live-access, or provide --local-file.[/yellow]")
        raise typer.Exit(1)
    if live and not confirm_live_access:
        console.print("[yellow]confirmation_required: CNKI live browser download requires --confirm-live-access.[/yellow]")
        raise typer.Exit(1)

    try:
        if local_file:
            artifact = client.materialize_downloaded_file(
                paper,
                local_file,
                source_url=source_url or detail_url,
                filename_policy=filename_policy,
                filename_template=filename_template,
            )
        else:
            console.print(
                "[yellow]CNKI live download may trigger a captcha or safety verification; "
                "please keep the visible browser open and be ready for manual captcha handling.[/yellow]"
            )
            live_download_dir = Path(cfg.cache_dir) / "cnki-live-downloads"
            artifact = client.download_cnki_artifact(
                paper,
                detail_url,
                prefer=prefer,
                filename_policy=filename_policy,
                filename_template=filename_template,
                confirm_live_access=confirm_live_access,
                mode=mode,
                debug_port=debug_port,
                download_dir=live_download_dir,
                timeout=timeout,
            )
    except (OSError, RuntimeError) as e:
        console.print(f"[red]CNKI artifact could not be saved: {e}[/red]")
        raise typer.Exit(1)

    console.print("[green]CNKI artifact saved.[/green]")
    console.print(f"Path: {artifact.path}")
    console.print(f"Format: {artifact.format}")
    console.print(f"Kind: {artifact.kind}")
    console.print(f"text_extracted={str(artifact.text_extracted).lower()}")
    if artifact.note:
        console.print(f"Note: {artifact.note}")


@app.command()
def cnki_batch_download(
    file: Path = typer.Argument(help="JSON/JSONL/plain-text file of CNKI detail URLs or item objects."),
    prefer: str = typer.Option("pdf", "--prefer", help="Preferred live download format."),
    filename_policy: str = typer.Option("", "--filename-policy", help="Filename policy: identifier, title_author, title_year_author, custom."),
    filename_template: str = typer.Option("", "--filename-template", help="Filename template for custom policy."),
    output: str = typer.Option("", "--output", "-o", help="Output directory."),
    live: bool = typer.Option(False, "--live", help="Enable gated visible-browser CNKI batch download."),
    confirm_live_access: bool = typer.Option(False, "--confirm-live-access", help="Required with --live."),
    mode: str = typer.Option("managed", "--mode", help="managed or attach."),
    debug_port: int = typer.Option(9222, "--debug-port", help="Chrome debug port for mode=attach."),
    timeout: int = typer.Option(45, "--timeout", help="Seconds to wait for each CNKI browser download."),
    min_interval: float = typer.Option(cnki.CNKI_MIN_INTERVAL_SECONDS, "--min-interval", help="Minimum seconds between CNKI downloads."),
    cooldown_every: int = typer.Option(cnki.CNKI_MAX_DOWNLOADS_PER_RUN, "--cooldown-every", help="Use long cooldown after every N attempted downloads."),
    cooldown_seconds: float = typer.Option(cnki.CNKI_MIN_INTERVAL_SECONDS * 3, "--cooldown-seconds", help="Long cooldown seconds."),
    max_consecutive_failures: int = typer.Option(1, "--max-consecutive-failures", help="Stop after this many consecutive failures/captcha timeouts."),
    state_file: str = typer.Option("", "--state-file", help="Batch state JSON path for resume."),
    resume: bool = typer.Option(False, "--resume", help="Resume from state file and skip completed/failed entries."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging."),
):
    """Run gated CNKI batch download with conservative throttling and resume state."""

    _setup_logging(verbose)
    if not file.exists() and not (resume and state_file):
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1)
    if not live:
        console.print("[yellow]CNKI batch live download requires --live and --confirm-live-access.[/yellow]")
        raise typer.Exit(1)
    if not confirm_live_access:
        console.print("[yellow]confirmation_required: CNKI batch live download requires --confirm-live-access.[/yellow]")
        raise typer.Exit(1)

    cfg = Config.load()
    if output:
        cfg.output_dir = output
    try:
        items = [] if resume and state_file and not file.exists() else _load_cnki_batch_items(file)
    except (OSError, json.JSONDecodeError) as e:
        console.print(f"[red]CNKI batch input could not be read: {e}[/red]")
        raise typer.Exit(1)
    if not items and not (resume and state_file):
        console.print("[yellow]No CNKI batch items found.[/yellow]")
        raise typer.Exit(0)

    console.print(
        "[yellow]CNKI batch live download may trigger captcha/safety verification; "
        "keep the visible browser open. This command will throttle, cooldown, and stop after repeated failures.[/yellow]"
    )
    client = cnki.CNKIClient(cfg)
    try:
        result = client.download_cnki_batch(
            items,
            prefer=prefer,
            filename_policy=filename_policy,
            filename_template=filename_template,
            confirm_live_access=confirm_live_access,
            mode=mode,
            debug_port=debug_port,
            download_dir=Path(cfg.cache_dir) / "cnki-live-downloads",
            timeout=timeout,
            state_file=state_file or None,
            resume=resume,
            min_interval_seconds=min_interval,
            cooldown_every=cooldown_every,
            cooldown_seconds=cooldown_seconds,
            max_consecutive_failures=max_consecutive_failures,
        )
    except (OSError, RuntimeError) as e:
        console.print(f"[red]CNKI batch download failed: {e}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]CNKI batch download:[/bold] {result.status}")
    console.print(f"State File: {result.state_path}")
    if getattr(result, "sidecar_path", None):
        console.print(f"Recovery Sidecar: {result.sidecar_path}")
    console.print(f"Succeeded: {result.succeeded}")
    console.print(f"Failed: {result.failed}")
    console.print(f"Pending: {result.pending}")
    if result.stopped_reason:
        console.print(f"Stopped Reason: {result.stopped_reason}")
    for idx, entry in enumerate(result.entries, 1):
        label = entry.item.title or entry.item.cnki_id or entry.item.detail_url
        console.print(f"{idx}. {entry.status}: {label}")
        if entry.artifact_path:
            console.print(f"   → {entry.artifact_path}")
        if entry.error:
            console.print(f"   error: {entry.error}")
    if result.status == "stopped":
        raise typer.Exit(1)


@app.command()
def cnki_smoke(
    query: str = typer.Option("", "--query", "-q", help="CNKI query for search-page smoke."),
    detail_url: str = typer.Option("", "--detail-url", help="CNKI detail URL for detail-page smoke."),
    limit: int = typer.Option(1, "--limit", help="Max records to parse during smoke; capped at 3."),
    mode: str = typer.Option("managed", "--mode", help="managed or attach."),
    dry_run: bool = typer.Option(True, "--dry-run/--live", help="Dry run never opens a browser; --live requires --confirm-live-access."),
    confirm_live_access: bool = typer.Option(False, "--confirm-live-access", help="Required for live CNKI visible-browser access."),
    search_type: str = typer.Option("theme", "--search-type", help="CNKI search type marker for the smoke URL."),
    debug_port: int = typer.Option(9222, "--debug-port", help="Chrome debug port for mode=attach."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging."),
):
    """Plan or run a tightly gated CNKI visible-browser smoke probe."""
    _setup_logging(verbose)
    result = cnki.run_visible_browser_smoke(
        query=query,
        detail_url=detail_url,
        limit=limit,
        mode=mode,
        dry_run=dry_run,
        confirm_live_access=confirm_live_access,
        search_type=search_type,
        debug_port=debug_port,
    )

    console.print(f"[bold]CNKI visible-browser smoke:[/bold] {result.status}")
    console.print(f"Dry Run: {str(result.dry_run).lower()}")
    console.print(f"Mode: {result.mode}")
    console.print(f"Limit: {result.limit}")
    if result.search_url:
        console.print(f"Search URL: {result.search_url}")
    if result.detail_url:
        console.print(f"Detail URL: {result.detail_url}")
    if result.page_state:
        console.print(f"Page State: {result.page_state}")
    if result.hits:
        console.print(f"Parsed Hits: {len(result.hits)}")
        for hit in result.hits[:3]:
            console.print(f"- {hit.title or '(untitled)'} [{hit.cnki_id or 'no-cnki-id'}]")
    if result.paper:
        console.print(f"Parsed Detail: {result.paper.title or '(untitled)'}")
    for warning in result.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")
    if result.next_action:
        console.print(f"Next Action: {result.next_action}")

    if result.status in {"invalid_mode", "invalid_url", "missing_target"}:
        raise typer.Exit(2)
    if result.status == "confirmation_required":
        raise typer.Exit(1)


@app.command()
def cnki_detail(
    url_or_id: str = typer.Option("", "--url-or-id", help="CNKI detail URL or filename/CNKI ID."),
    html_file: str = typer.Option("", "--html-file", help="Captured CNKI detail page HTML/page-source file."),
    format: str = typer.Option("markdown", "--format", "-f", help="Output format: markdown, json, text."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging."),
):
    """Parse CNKI detail metadata from supplied HTML without live access."""
    _setup_logging(verbose)
    try:
        result = cnki.get_cnki_detail(url_or_id, html_file=html_file)
    except OSError as e:
        console.print(f"[red]CNKI detail HTML could not be read: {e}[/red]")
        raise typer.Exit(1)

    if result.status != "ok" or result.paper is None:
        console.print(f"[yellow]CNKI detail unavailable: {result.status}[/yellow]")
        if result.url:
            console.print(f"URL: {result.url}")
        for warning in result.warnings:
            console.print(f"[yellow]Warning:[/yellow] {warning}")
        if result.next_action:
            console.print(f"Next Action: {result.next_action}")
        raise typer.Exit(1)

    fmt = (format or "markdown").lower()
    if fmt == "json":
        console.print(result.paper.to_json())
    elif fmt == "text":
        console.print(result.paper.to_text())
    else:
        console.print(result.paper.to_markdown(include_pdf_path=True))


@app.command()
def cnki_search_html(
    query: str = typer.Option(..., "--query", "-q", help="Original CNKI query for the captured search page."),
    html_file: str = typer.Option(..., "--html-file", help="Captured CNKI search result HTML/page-source file."),
    limit: int = typer.Option(10, "--limit", help="Maximum records to parse."),
    base_url: str = typer.Option("https://kns.cnki.net/", "--base-url", help="Base URL used to resolve relative CNKI links."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging."),
):
    """Parse captured CNKI search HTML into a saved SearchSession without live access."""
    _setup_logging(verbose)
    cfg = Config.load()
    try:
        session = cnki.search_cnki_from_html_file(
            query,
            html_file,
            limit=limit,
            cache_dir=cfg.cache_dir,
            base_url=base_url,
        )
    except OSError as e:
        console.print(f"[red]CNKI search HTML could not be read: {e}[/red]")
        raise typer.Exit(1)

    console.print("[green]CNKI search HTML parsed.[/green]")
    console.print(f"Search Session: {session.session_id}")
    console.print(f"Results: {len(session.hits)}")
    for err in session.errors:
        console.print(f"[yellow]{err.source}/{err.code}:[/yellow] {err.message}")
    for idx, hit in enumerate(session.hits[:limit], 1):
        console.print(f"{idx}. {hit.title or '(untitled)'}")
        if hit.cnki_id:
            console.print(f"   CNKI ID: {hit.cnki_id}")
        if hit.source_url:
            console.print(f"   Source URL: {hit.source_url}")


@app.command()
def carsi_login(
    publisher: str = typer.Option("", "--publisher", "-p", help="Publisher (sciencedirect, springer, wiley, ieee, tandfonline, nature). Omit to pick from article URL."),
    url: str = typer.Option("", "--url", "-u", help="Article URL to auto-detect publisher."),
    force: bool = typer.Option(False, "--force", "-f", help="Force re-login."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging."),
):
    """Authenticate via CARSI/Shibboleth federated login."""
    _setup_logging(verbose)
    config = Config.load()

    if not config.carsi_enabled:
        console.print("[red]CARSI is not enabled. Run: vpnsci-sustech config-cmd --carsi-enable --carsi-school \"你的学校名\"[/red]")
        raise typer.Exit(1)

    if not config.carsi_idp_name:
        console.print("[red]CARSI school not set. Run: vpnsci-sustech config-cmd --carsi-school \"你的学校名\"[/red]")
        raise typer.Exit(1)

    if not publisher and url:
        from .carsi import detect_publisher
        publisher = detect_publisher(url) or ""

    if not publisher:
        console.print("[yellow]Available publishers:[/yellow]")
        console.print("  sciencedirect, springer, wiley, ieee, tandfonline, nature")
        publisher = typer.prompt("Enter publisher name")

    from .carsi import CARSIClient
    carsi = CARSIClient(config)
    try:
        console.print(f"[bold]CARSI login for: {publisher}[/bold]")
        console.print(f"[dim]School: {config.carsi_idp_name}[/dim]")
        if carsi.login(publisher, force=force):
            console.print("[green]CARSI session established![/green]")
        else:
            console.print("[red]CARSI login failed.[/red]")
            raise typer.Exit(1)
    finally:
        carsi.close()


if __name__ == "__main__":
    app()
