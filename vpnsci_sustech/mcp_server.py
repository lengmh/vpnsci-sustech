"""MCP server exposing vpnsci-sustech tools for AI agents supporting MCP protocol."""

import asyncio
import json
import logging
import sys
from typing import Literal
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context
from pydantic import BaseModel

from . import report_bridge
from .config import Config
from .fetcher import PaperFetcher
from .models import Paper
from .report_recovery import resolve_report_recovery_session
from .sources import backend_routing, cnki, publisher_search, search_mode, semantic_scholar, standard_search
from .sources.search_cache import load_session, save_session

# Logging must go to stderr (stdout is used by MCP stdio transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

mcp = FastMCP("vpnsci-sustech")

# Lazy-initialized shared fetcher instance
_fetcher: PaperFetcher | None = None

def _get_fetcher() -> PaperFetcher | None:
    """Get or create the fetcher singleton.

    Allows CARSI-only usage even when `school` is empty, which is the main
    SUSTech path for this fork.
    """
    global _fetcher
    config = Config.load()
    has_school = bool(config.school)
    has_carsi_only = bool(config.carsi_enabled and config.carsi_idp_name)
    if not has_school and not has_carsi_only:
        return None
    if _fetcher is None:
        _fetcher = PaperFetcher(config)
    return _fetcher


def _reset_fetcher():
    """Reset the fetcher singleton (called after reconfiguring school)."""
    global _fetcher
    if _fetcher is not None:
        _fetcher.close()
        _fetcher = None


_SCHOOL_NOT_CONFIGURED = (
    "⚠️ 尚未配置可用访问方式。\n\n"
    "你可以二选一：\n"
    "1. 配置内置学校：vpnsci-sustech config-cmd --school 学校名称\n"
    "2. 走 CARSI-only：vpnsci-sustech config-cmd --carsi-enable --carsi-school \"Southern University of Science and Technology\""
)

UPGRADE_SUGGESTION_TEXT = (
    "如果你想要更全面覆盖、去重整合和 HTML 综合报告，"
    "我可以基于这次检索继续进入“专业调研”模式。"
)


class FilenamePolicyChoice(BaseModel):
    policy: Literal["identifier", "title_author", "title_year_author"] = "title_author"


def _cnki_batch_items_from_payload(items) -> list[cnki.CNKIBatchItem]:
    """Normalize MCP list payload into CNKIBatchItem objects."""

    normalized: list[cnki.CNKIBatchItem] = []
    for item in items or []:
        if isinstance(item, cnki.CNKIBatchItem):
            normalized.append(item)
            continue
        if isinstance(item, str):
            value = item.strip()
            if value:
                normalized.append(cnki.CNKIBatchItem(detail_url=value, source_url=value))
            continue
        if not isinstance(item, dict):
            continue
        detail_url = str(item.get("detail_url") or item.get("url") or "").strip()
        if not detail_url:
            continue
        normalized.append(
            cnki.CNKIBatchItem(
                detail_url=detail_url,
                title=str(item.get("title") or ""),
                first_author=str(item.get("first_author") or item.get("firstAuthor") or ""),
                cnki_id=str(item.get("cnki_id") or item.get("cnkiId") or ""),
                source_url=str(item.get("source_url") or item.get("sourceUrl") or detail_url),
            )
        )
    return normalized


def _render_cnki_batch_result(result: cnki.CNKIBatchResult) -> str:
    lines = [
        f"CNKI batch download: {result.status}",
        "",
        f"- State File: `{result.state_path}`",
        f"- Succeeded: {result.succeeded}",
        f"- Failed: {result.failed}",
        f"- Pending: {result.pending}",
    ]
    if getattr(result, "sidecar_path", None):
        lines.append(f"- Recovery Sidecar: `{result.sidecar_path}`")
    if result.stopped_reason:
        lines.append(f"- Stopped Reason: `{result.stopped_reason}`")
    if result.entries:
        lines.append("- Entries:")
        for idx, entry in enumerate(result.entries, 1):
            label = entry.item.title or entry.item.cnki_id or entry.item.detail_url
            line = f"  {idx}. `{entry.status}` — {label}"
            if entry.artifact_path:
                line += f" → `{entry.artifact_path}`"
            if entry.error:
                line += f" — error: {entry.error}"
            lines.append(line)
    return "\n".join(lines)


def _render_search_results(results, *, session=None) -> str:
    """Render unified search hits for MCP responses."""

    if not results:
        if session is not None and getattr(session, "errors", None):
            lines = ["No results returned from available search sources.\n"]
            lines.append(f"Search Session: `{session.session_id}`")
            lines.append("Source Errors:")
            for err in session.errors:
                lines.append(f"- **{err.source} / {err.code}:** {err.message}")
            return "\n".join(lines)
        return "No results found."

    lines = [f"Found {len(results)} results:\n"]
    if session is not None:
        lines.append(f"Search Session: `{session.session_id}`")
        if session.source_summary:
            summary = ", ".join(f"{k}={v}" for k, v in session.source_summary.items())
            lines.append(f"Source Summary: {summary}")
        lines.append("")

    for i, r in enumerate(results, 1):
        authors_str = ", ".join(r.authors[:3])
        if len(r.authors) > 3:
            authors_str += " et al."

        lines.append(f"### {i}. {r.title}")
        lines.append(f"- **Authors:** {authors_str}")
        if r.year:
            lines.append(f"- **Year:** {r.year}")
        if r.journal:
            lines.append(f"- **Journal:** {r.journal}")
        if r.doi:
            lines.append(f"- **DOI:** {r.doi}")
        elif r.arxiv_id:
            lines.append(f"- **arXiv:** {r.arxiv_id}")
        if getattr(r, "cnki_id", ""):
            lines.append(f"- **CNKI ID:** {r.cnki_id}")
        if getattr(r, "source_url", ""):
            lines.append(f"- **Source URL:** {r.source_url}")
        if getattr(r, "result_type", ""):
            lines.append(f"- **Result Type:** {r.result_type}")
        if getattr(r, "download_format", ""):
            lines.append(f"- **Download Format:** {r.download_format}")
        if getattr(r, "local_file", ""):
            lines.append(f"- **Local File:** {r.local_file}")
        lines.append(f"- **Citations:** {getattr(r, 'citation_count', 0)}")
        if getattr(r, "url", ""):
            lines.append(f"- **URL:** {r.url}")
        if getattr(r, "pdf_url", ""):
            lines.append(f"- **PDF URL:** {r.pdf_url}")
        if getattr(r, "sources", None):
            lines.append(f"- **Sources:** {', '.join(r.sources)}")
        if r.abstract:
            lines.append(f"- **Abstract:** {r.abstract[:200]}...")
        lines.append("")

    if session is not None and session.upgrade_suggested:
        lines.append(UPGRADE_SUGGESTION_TEXT)
    return "\n".join(lines)


@mcp.tool()
async def configure_school(school_name: str) -> str:
    """Configure which university to use for WebVPN paper access.

    Call this when the user tells you their school name.
    Supports fuzzy matching (e.g. "兰大" will match "兰州大学").

    Args:
        school_name: The university name (e.g. "兰州大学", "清华大学").
    """
    from .schools import get_school

    try:
        entry = get_school(school_name)
    except ValueError:
        return (
            f"未找到学校「{school_name}」。"
            f"请确认学校名称，或使用 vpnsci-sustech schools 搜索支持的学校列表。"
        )

    config = Config.load()
    config.school = entry.name
    if entry.school_type == "ezproxy":
        config.ezproxy_base_url = entry.host
        config.webvpn_base_url = ""
    else:
        config.webvpn_base_url = entry.host
        config.ezproxy_base_url = ""
    config.save()

    # Reset fetcher so it picks up the new config
    _reset_fetcher()

    # Provide school-type-specific guidance
    type_guidance = ""
    if entry.school_type == "easyconnect":
        type_guidance = (
            "\n\n⚠️ **该校使用 EasyConnect VPN**，需要额外配置才能获取论文：\n"
            "1. **推荐方案**：使用 [docker-easyconnect](https://github.com/Hagb/docker-easyconnect)\n"
            "   ```bash\n"
            "   docker run --rm -d --name easyconnect --privileged \\\n"
            "     -p 127.0.0.1:1080:1080 -p 127.0.0.1:8888:8888 \\\n"
            "     -e EC_VER=7.6.3 -e VPN_ADDR=<VPN地址> hagb/docker-easyconnect\n"
            "   ```\n"
            "2. 浏览器打开 `http://127.0.0.1:8888` 完成登录\n"
            "3. 登录成功后设置代理：`vpnsci-sustech config-cmd --proxy-url socks5://127.0.0.1:1080`\n\n"
            "部分学校也可尝试 [zju-connect](https://github.com/THU-wzj/zju-connect)（更轻量但兼容性有限）。"
        )
    elif entry.school_type == "atrust":
        gateway = entry.gateway or entry.host.replace("https://", "").replace("http://", "")
        type_guidance = (
            f"\n\n⚠️ **该校使用 aTrust 零信任 VPN**，需要 Docker 方案：\n"
            "1. 安装 Docker Desktop 并启动\n"
            "2. 运行 docker-easyconnect（aTrust 模式）：\n"
            "   ```bash\n"
            "   docker run --rm -d --name easyconnect --privileged \\\n"
            "     -p 127.0.0.1:1080:1080 -p 127.0.0.1:8888:8888 \\\n"
            f"     -e EC_VER=7.6.3 -e VPN_ADDR={gateway} hagb/docker-easyconnect\n"
            "   ```\n"
            "3. 浏览器打开 `http://127.0.0.1:8888` 完成登录\n"
            "4. 登录成功后设置代理：`vpnsci-sustech config-cmd --proxy-url socks5://127.0.0.1:1080`\n\n"
            "注意：aTrust 不支持 zju-connect，必须使用 docker-easyconnect。"
        )
    elif entry.school_type == "ezproxy":
        type_guidance = (
            "\n\n📚 **该校使用 EZproxy 图书馆代理**。首次获取论文时会弹出浏览器，"
            "完成学校图书馆登录即可。"
        )

    type_label = {"webvpn": "WebVPN", "easyconnect": "EasyConnect", "atrust": "aTrust", "ezproxy": "EZproxy"}.get(entry.school_type, entry.school_type)

    return (
        f"✅ 已配置为 **{entry.name}**（{entry.province}）\n"
        f"代理地址: {entry.host}\n"
        f"类型: {type_label}{type_guidance}\n\n"
        f"现在可以开始搜索和获取论文了。"
    )


@mcp.tool()
async def configure_carsi_school(carsi_school_name: str) -> str:
    """Configure CARSI/Shibboleth school name directly.

    This is the recommended SUSTech path for this fork, even if the school is
    not in the upstream built-in school list.
    """
    config = Config.load()
    config.carsi_enabled = True
    config.carsi_idp_name = carsi_school_name
    config.save()
    _reset_fetcher()
    return (
        f"✅ 已启用 CARSI，并设置学校为：{carsi_school_name}\n\n"
        "对于南方科技大学，推荐保持 school 为空，优先走 CARSI 路径。"
    )


async def _resolve_mcp_filename_policy(
    *,
    explicit_policy: str = "",
    ask_rename: bool = False,
    ctx: Context | None = None,
) -> str:
    if explicit_policy:
        return explicit_policy
    if ctx is None or not hasattr(ctx, "elicit"):
        return ""

    cfg = Config.load()
    default_policy = getattr(cfg, "paper_filename_policy", "title_author") or "title_author"
    config_ask = bool(getattr(cfg, "paper_filename_ask", False))
    if not (ask_rename or config_ask):
        return ""

    message = (
        "请选择本次下载的文献文件命名策略。"
        f"当前配置默认是 `{default_policy}`；这次选择只影响本次下载。"
        "可在 config.json 或 `vpnsci-sustech config-cmd --paper-filename-policy ...` 中修改默认值；"
        "也可设置 `paper_filename_ask=false` 或运行 `vpnsci-sustech config-cmd --paper-filename-ask false` 关闭后续主动询问。"
    )
    try:
        result = await ctx.elicit(message, FilenamePolicyChoice)
    except Exception as e:
        logger.info("Filename policy elicitation unavailable, using config default: %s", e)
        return ""

    if getattr(result, "action", "") != "accept" or getattr(result, "data", None) is None:
        return ""
    return getattr(result.data, "policy", "") or ""


@mcp.tool()
async def fetch_paper(
    identifier: str,
    format: str = "markdown",
    filename_policy: str = "",
    filename_template: str = "",
    ask_rename: bool = False,
    ctx: Context | None = None,
) -> str:
    """Fetch an academic paper's full text by DOI or URL.

    Uses Open Access sources (Unpaywall, arXiv) first, then falls back
    to WebVPN/EZproxy for paywalled content. Results are cached locally.

    Args:
        identifier: DOI (e.g. "10.1038/nphys1509") or article URL.
        format: Output format - "markdown" (default), "json", or "text".
        filename_policy: Optional filename policy: identifier, title_author, title_year_author, or custom.
        filename_template: Optional template used when filename_policy is custom.
        ask_rename: Ask the MCP client once for this download's filename policy when supported.
    """
    fetcher = _get_fetcher()
    if fetcher is None:
        return _SCHOOL_NOT_CONFIGURED

    resolved_policy = await _resolve_mcp_filename_policy(
        explicit_policy=filename_policy,
        ask_rename=ask_rename,
        ctx=ctx,
    )
    paper = await asyncio.to_thread(
        fetcher.fetch,
        identifier,
        filename_policy=resolved_policy,
        filename_template=filename_template,
    )

    if not paper.full_text and not paper.abstract:
        return f"Could not extract full text for: {identifier}\nTitle: {paper.title}\nURL: {paper.url}"

    if format == "json":
        return paper.to_json()
    elif format == "text":
        return paper.to_text()
    else:
        return paper.to_markdown(include_pdf_path=True)


@mcp.tool()
async def fetch_search_hit(
    session_id: str,
    hit_key: str,
    filename_policy: str = "",
    filename_template: str = "",
    confirm_live_access: bool = False,
) -> str:
    """Continue full-text fetch from one SearchSession hit."""
    fetcher = _get_fetcher()
    if fetcher is None:
        return _SCHOOL_NOT_CONFIGURED
    session = load_session(session_id, Path(Config.load().cache_dir))
    hit = next((item for item in session.hits if item.hit_key == hit_key), None)
    if hit is None:
        return f"Hit not found: {hit_key}"
    paper = await asyncio.to_thread(
        fetcher.fetch_from_search_hit,
        hit,
        filename_policy=filename_policy,
        filename_template=filename_template,
        confirm_live_access=confirm_live_access,
    )
    return paper.to_markdown(include_pdf_path=True)


@mcp.tool()
async def search_papers(query: str, limit: int = 10, year_range: str = "", backend: str = "") -> str:
    """Search for academic papers.

    Returns a list of papers with titles, authors, DOIs, and citation counts.
    Use the DOIs from results with fetch_paper to get full text.

    Args:
        query: Search query (e.g. "organic photovoltaics silver nanowire").
        limit: Maximum number of results (1-100, default 10).
        year_range: Optional year filter (e.g. "2020-2024" or "2020-").
        backend: Optional publisher-native backend: sciencedirect, springerlink, wiley, ieee.
    """
    config = Config.load()
    route = backend_routing.resolve_requested_backend(query, explicit_backend=backend)
    if route.backend == "cnki":
        session = await asyncio.to_thread(
            cnki.search_cnki,
            query,
            limit=limit,
            config=config,
        )
        return _render_search_results(session.hits, session=session)

    if route.backend:
        try:
            results = await asyncio.to_thread(
                publisher_search.search,
                query,
                backend=route.backend,
                limit=limit,
            )
        except publisher_search.PublisherSearchBlockedError as e:
            return (
                f"⚠️ publisher-native search blocked for `{route.backend}`.\n\n"
                f"原因：{e}\n"
                "当前返回更像 challenge / anti-bot / access-control，而不是正常无结果。"
            )
        return _render_search_results(results)
    else:
        mode_decision = search_mode.classify_search_mode(query, {})
        session = await asyncio.to_thread(
            standard_search.search,
            query,
            limit=limit,
            year_range=year_range or None,
            config=config,
        )
        if mode_decision.mode != "pro":
            return _render_search_results(session.hits, session=session)

        try:
            report = await asyncio.to_thread(
                report_bridge.start_report_from_session,
                session.session_id,
                config=config,
                mode="full",
                display_query=query,
                language="zh" if any("\u4e00" <= ch <= "\u9fff" for ch in query) else "en",
                open_report=True,
            )
        except report_bridge.ReportBridgeConfigError as e:
            return (
                "已识别为“专业调研”请求，但报告桥接尚未配置。\n\n"
                f"- Search Session: `{session.session_id}`\n"
                f"- 原因：{e}\n\n"
                "已先完成标准检索并保存为种子会话：\n\n"
                f"{_render_search_results(session.hits, session=session)}"
            )
        except report_bridge.ReportBridgeError as e:
            return (
                "已识别为“专业调研”请求，但报告生成失败。\n\n"
                f"- Search Session: `{session.session_id}`\n"
                f"- 原因：{e}\n\n"
                "标准检索结果仍可用于继续全文获取：\n\n"
                f"{_render_search_results(session.hits, session=session)}"
            )

        if getattr(report, "status", "") == "handoff_required":
            return (
                "已识别为“专业调研”请求；完整 paper-search-pro workflow 需要 handoff。\n\n"
                f"- Search Session: `{report.seed_session_id}`\n"
                f"- Report Mode: `{report.report_mode}`\n"
                f"- Status: `{report.status}`\n"
                f"- Handoff: `{report.handoff_path}`\n"
                "- Automation: Codex 会话层读取 handoff 后继续跑 full workflow\n"
                "- Multi-agent: 需要 `multi_agent_v1.spawn_agent` 启动并行 SubAgent\n"
                "- Failure policy: SubAgent 启动失败/超时/输出无效会在当前对话内汇报，不会静默退回 seed_preview\n"
                f"- Deduped Papers: {report.deduped_paper_count}\n"
                "没有把 seed-only preview 冒充为完整专业调研。"
            )

        return (
            "✅ 已按“专业调研”请求启动报告生成。\n\n"
            f"- Search Session: `{report.seed_session_id}`\n"
            f"- Report Mode: `{report.report_mode}`\n"
            f"- Status: `{report.status}`\n"
            f"- PID: `{report.pid}`\n"
            f"- Link: [打开 HTML 报告]({report.file_url})\n"
            f"- Local Path: `{report.report_path}`\n"
            "- Tip: 如果链接在 Agent 代码编辑器内打开，请右键 HTML 文件标签，选择“在资源管理器中显示/打开”，再用浏览器打开原文件。\n"
            f"- Log: `{report.log_path}`\n"
            f"- Deduped Papers: {report.deduped_paper_count}\n"
            f"- Expanded Sources: {', '.join(report.expanded_sources) if report.expanded_sources else '(none)'}\n"
            "报告在后台生成；如文件暂未出现，请稍后查看 Report 路径或 Log。"
        )


@mcp.tool()
async def download_cnki_artifact(
    detail_url: str = "",
    local_file: str = "",
    prefer: str = "pdf",
    title: str = "",
    first_author: str = "",
    cnki_id: str = "",
    source_url: str = "",
    filename_policy: str = "",
    filename_template: str = "",
    live: bool = False,
    confirm_live_access: bool = False,
    mode: str = "managed",
    debug_port: int = 9222,
    timeout: int = 45,
) -> str:
    """Save a CNKI artifact through the project filename/artifact model.

    Live CNKI browser download is tightly gated. Prefer local_file unless the
    user explicitly confirms a visible-browser smoke download.

    Args:
        detail_url: CNKI detail URL for future visible-browser download.
        local_file: Existing local PDF/CAJ/CAJX/NH/KDH file to materialize.
        prefer: Preferred live download format, currently gated.
        title: Paper title used for filename metadata.
        first_author: First author used for filename metadata.
        cnki_id: CNKI identifier.
        source_url: Original CNKI source/download URL.
        filename_policy: Optional filename policy: identifier, title_author, title_year_author, or custom.
        filename_template: Optional template used when filename_policy is custom.
        live: Enable visible-browser CNKI download.
        confirm_live_access: Required with live.
        mode: managed or attach.
        debug_port: Chrome debug port for mode=attach.
        timeout: Seconds to wait for one CNKI browser download.
    """

    config = Config.load()
    paper = Paper(
        title=title,
        authors=[first_author] if first_author else [],
        source="cnki",
        url=detail_url or source_url,
    )
    setattr(paper, "cnki_id", cnki_id)
    client = cnki.CNKIClient(config)

    if local_file:
        try:
            artifact = await asyncio.to_thread(
                client.materialize_downloaded_file,
                paper,
                local_file,
                source_url=source_url or detail_url,
                filename_policy=filename_policy,
                filename_template=filename_template,
            )
        except OSError as e:
            return f"⚠️ CNKI local file could not be saved: {e}"
        return (
            "✅ CNKI artifact saved.\n\n"
            f"- Path: `{artifact.path}`\n"
            f"- Format: `{artifact.format}`\n"
            f"- Kind: `{artifact.kind}`\n"
            f"- text_extracted={str(artifact.text_extracted).lower()}\n"
            f"- Note: {artifact.note or '(none)'}"
        )

    if not live:
        return (
            "⚠️ CNKI live browser download requires `live=true` and "
            "`confirm_live_access=true`, or provide `local_file`."
        )
    if not confirm_live_access:
        return "⚠️ confirmation_required: CNKI live browser download requires explicit user confirmation."
    if not detail_url:
        return "⚠️ missing_target: provide a CNKI detail_url for live download."

    try:
        live_download_dir = Path(config.cache_dir) / "cnki-live-downloads"
        artifact = await asyncio.to_thread(
            client.download_cnki_artifact,
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
        return f"⚠️ CNKI artifact could not be saved: {e}"

    if artifact is None:
        return "⚠️ CNKI artifact could not be saved: no downloaded file was found."
    return (
        "ℹ️ CNKI live download may trigger a captcha or safety verification; "
        "please keep the visible browser open and be ready for manual captcha handling.\n\n"
        "✅ CNKI artifact saved.\n\n"
        f"- Path: `{artifact.path}`\n"
        f"- Format: `{artifact.format}`\n"
        f"- Kind: `{artifact.kind}`\n"
        f"- text_extracted={str(artifact.text_extracted).lower()}\n"
        f"- Note: {artifact.note or '(none)'}"
    )


@mcp.tool()
async def download_cnki_batch_artifacts(
    items: list[dict] | list[str],
    prefer: str = "pdf",
    filename_policy: str = "",
    filename_template: str = "",
    live: bool = False,
    confirm_live_access: bool = False,
    mode: str = "managed",
    debug_port: int = 9222,
    timeout: int = 45,
    min_interval_seconds: float = cnki.CNKI_MIN_INTERVAL_SECONDS,
    cooldown_every: int = cnki.CNKI_MAX_DOWNLOADS_PER_RUN,
    cooldown_seconds: float = cnki.CNKI_MIN_INTERVAL_SECONDS * 3,
    max_consecutive_failures: int = 1,
    state_file: str = "",
    resume: bool = False,
) -> str:
    """Run gated CNKI batch download with throttling, cooldown, stop, and resume state.

    Args:
        items: List of CNKI detail URL strings or objects with detail_url/title/first_author/cnki_id.
        live: Must be true for browser download.
        confirm_live_access: Required with live.
        state_file: Optional JSON state path; use with resume=true to continue pending entries.
    """

    if not live:
        return "⚠️ CNKI batch live download requires `live=true` and `confirm_live_access=true`."
    if not confirm_live_access:
        return "⚠️ confirmation_required: CNKI batch live download requires explicit user confirmation."

    config = Config.load()
    batch_items = _cnki_batch_items_from_payload(items)
    if not batch_items and not (resume and state_file):
        return "⚠️ CNKI batch download has no items. Provide `items` or `resume=true` with `state_file`."

    client = cnki.CNKIClient(config)
    try:
        result = await asyncio.to_thread(
            client.download_cnki_batch,
            batch_items,
            prefer=prefer,
            filename_policy=filename_policy,
            filename_template=filename_template,
            confirm_live_access=confirm_live_access,
            mode=mode,
            debug_port=debug_port,
            download_dir=Path(config.cache_dir) / "cnki-live-downloads",
            timeout=timeout,
            state_file=state_file or None,
            resume=resume,
            min_interval_seconds=min_interval_seconds,
            cooldown_every=cooldown_every,
            cooldown_seconds=cooldown_seconds,
            max_consecutive_failures=max_consecutive_failures,
        )
    except (OSError, RuntimeError) as e:
        return f"⚠️ CNKI batch download failed: {e}"

    return (
        "ℹ️ CNKI batch live download may trigger captcha/safety verification; "
        "keep the visible browser open. No captcha bypass is attempted.\n\n"
        + _render_cnki_batch_result(result)
    )


def _render_cnki_smoke_result(result: cnki.CNKIVisibleSmokeResult) -> str:
    lines = [
        f"CNKI visible-browser smoke: {result.status}",
        "",
        f"- Dry Run: {str(result.dry_run).lower()}",
        f"- Mode: `{result.mode}`",
        f"- Limit: {result.limit}",
    ]
    if result.query:
        lines.append(f"- Query: {result.query}")
    if result.search_url:
        lines.append(f"- Search URL: {result.search_url}")
    if result.detail_url:
        lines.append(f"- Detail URL: {result.detail_url}")
    if result.page_state:
        lines.append(f"- Page State: {result.page_state}")
    if result.hits:
        lines.append(f"- Parsed Hits: {len(result.hits)}")
        for idx, hit in enumerate(result.hits[:3], 1):
            lines.append(f"  {idx}. {hit.title or '(untitled)'}")
            if hit.cnki_id:
                lines.append(f"     CNKI ID: {hit.cnki_id}")
    if result.paper:
        lines.append(f"- Parsed Detail: {result.paper.title or '(untitled)'}")
        cnki_id = getattr(result.paper, "cnki_id", "")
        if cnki_id:
            lines.append(f"- CNKI ID: {cnki_id}")
    if result.warnings:
        lines.append("- Warnings:")
        lines.extend(f"  - {warning}" for warning in result.warnings)
    if result.next_action:
        lines.append(f"- Next Action: {result.next_action}")
    return "\n".join(lines)


def _render_cnki_detail_result(result: cnki.CNKIDetailResult, output_format: str = "markdown") -> str:
    fmt = (output_format or "markdown").lower()
    if result.status == "ok" and result.paper:
        if fmt == "json":
            return result.paper.to_json()
        if fmt == "text":
            return result.paper.to_text()
        return result.paper.to_markdown(include_pdf_path=True)

    lines = [f"⚠️ CNKI detail unavailable: {result.status}"]
    if result.url:
        lines.append(f"- URL: {result.url}")
    if result.page_state:
        lines.append(f"- Page State: {result.page_state}")
    if result.warnings:
        lines.append("- Warnings:")
        lines.extend(f"  - {warning}" for warning in result.warnings)
    if result.next_action:
        lines.append(f"- Next Action: {result.next_action}")
    return "\n".join(lines)


@mcp.tool()
async def cnki_visible_smoke(
    query: str = "",
    detail_url: str = "",
    limit: int = 1,
    mode: str = "managed",
    dry_run: bool = True,
    confirm_live_access: bool = False,
    search_type: str = "theme",
    debug_port: int = 9222,
) -> str:
    """Plan or run a tightly gated CNKI visible-browser smoke probe.

    Default is dry_run and never opens a browser. Live execution requires
    dry_run=false and confirm_live_access=true.
    """

    result = await asyncio.to_thread(
        cnki.run_visible_browser_smoke,
        query=query,
        detail_url=detail_url,
        limit=limit,
        mode=mode,
        dry_run=dry_run,
        confirm_live_access=confirm_live_access,
        search_type=search_type,
        debug_port=debug_port,
    )
    return _render_cnki_smoke_result(result)


@mcp.tool()
async def get_cnki_paper_detail(
    url_or_id: str = "",
    html: str = "",
    html_file: str = "",
    format: str = "markdown",
) -> str:
    """Parse CNKI paper detail metadata from supplied HTML/page-source.

    This tool does not access CNKI. Provide html or html_file captured from a
    user-controlled browser or from cnki_visible_smoke.
    """

    result = await asyncio.to_thread(
        cnki.get_cnki_detail,
        url_or_id,
        html=html,
        html_file=html_file,
    )
    return _render_cnki_detail_result(result, output_format=format)


@mcp.tool()
async def search_cnki_from_html(
    query: str,
    html: str = "",
    html_file: str = "",
    limit: int = 10,
    base_url: str = "https://kns.cnki.net/",
) -> str:
    """Parse captured CNKI search-result HTML into a saved SearchSession.

    This tool does not access CNKI. Provide html or html_file captured from a
    user-controlled browser or from cnki_visible_smoke.
    """

    if not html and not html_file:
        return (
            "⚠️ CNKI HTML search unavailable: live_access_not_enabled\n"
            "- Warnings:\n"
            "  - 未提供 HTML；本工具不会直接访问 CNKI。\n"
            "- Next Action: 提供 html/html_file，或先运行 cnki-smoke dry-run/visible-browser smoke 获取页面快照。"
        )
    try:
        session = await asyncio.to_thread(
            cnki.search_cnki_from_html_file if html_file else cnki.search_cnki_from_html,
            query,
            html_file if html_file else html,
            limit=limit,
            cache_dir=Config.load().cache_dir,
            base_url=base_url,
        )
    except OSError as e:
        return f"⚠️ CNKI HTML search file could not be read: {e}"
    return _render_search_results(session.hits, session=session)


@mcp.tool()
async def generate_search_report(
    search_session_id: str,
    mode: str = "full",
    display_query: str = "",
    language: str = "",
    open_report: bool = True,
    query_title: str = "",
) -> str:
    """Generate an HTML research report from a saved search session.

    This is the explicit professional-research upgrade path. It uses the saved
    standard-search session as seed input for the configured paper-search-pro
    bridge. It is not called by normal search automatically.

    Agent automation contract:
        When mode="full" returns status="handoff_required", an Agent host that
        supports SubAgents should read the handoff package and continue the full
        upstream paper-search-pro workflow in the conversation/session layer.
        The MCP Python process does not directly call Codex-only multi_agent_v1
        tools. If SubAgents cannot start, time out, or return invalid output,
        the Agent should report the failure in the current conversation and must
        not silently downgrade to mode="seed_preview".

    Args:
        search_session_id: Search session id returned by search_papers.
        mode: "full" targets the full paper-search-pro workflow. "seed_preview"
            renders only the saved search session into a quick HTML preview.
        display_query: Optional human-friendly query/title shown in the report.
        language: Optional report UI language: "zh" or "en".
        open_report: Open the generated report in the default browser after rendering.
        query_title: Backward-compatible alias for display_query.
    """
    if query_title and not display_query:
        display_query = query_title
    if not language:
        language = "zh" if any("\u4e00" <= ch <= "\u9fff" for ch in display_query) else ""

    try:
        result = await asyncio.to_thread(
            report_bridge.start_report_from_session,
            search_session_id,
            config=Config.load(),
            mode=mode,
            display_query=display_query,
            language=language,
            open_report=open_report,
        )
    except report_bridge.ReportBridgeConfigError as e:
        return (
            "⚠️ 报告桥接尚未配置。\n\n"
            f"原因：{e}\n"
            "标准检索结果不受影响。请先配置 paper_search_pro_root 和 paper_search_pro_command。"
        )
    except report_bridge.ReportBridgeError as e:
        return (
            "⚠️ 报告生成失败。\n\n"
            f"原因：{e}\n"
            "标准检索结果不受影响，可以稍后重试或检查 paper-search-pro 配置。"
        )

    if getattr(result, "status", "") == "handoff_required":
        return (
            "⚠️ 完整专业调研需要 handoff。\n\n"
            f"- Search Session: `{result.seed_session_id}`\n"
            f"- Report Mode: `{result.report_mode}`\n"
            f"- Status: `{result.status}`\n"
            f"- Handoff: `{result.handoff_path}`\n"
            "- Automation: Codex 会话层读取 handoff 后继续跑 full workflow\n"
            "- Multi-agent: 需要 `multi_agent_v1.spawn_agent` 启动并行 SubAgent\n"
            "- Failure policy: SubAgent 启动失败/超时/输出无效会在当前对话内汇报，不会静默退回 seed_preview\n"
            f"- Deduped Papers: {result.deduped_paper_count}\n"
            f"- Expanded Sources: {', '.join(result.expanded_sources) if result.expanded_sources else '(none)'}\n"
            "当前未启动 HTML 生成；没有把 seed-only preview 冒充为完整 paper-search-pro workflow。"
        )
    if getattr(result, "status", "") == "theme_postprocess_required":
        return (
            "⚠️ 主题后处理需要 host Agent 接管。\n\n"
            f"- Search Session: `{result.seed_session_id}`\n"
            f"- Report Mode: `{result.report_mode}`\n"
            f"- Status: `{result.status}`\n"
            f"- Materialized Dir: `{result.materialized_dir}`\n"
            f"- Request: `{result.theme_postprocess_request_path}`\n"
            f"- Result Target: `{result.theme_postprocess_result_path}`\n"
            f"- Query: `{result.user_query}`\n"
            f"- Language: `{result.language}`\n"
            "- Automation: host Agent 应读取 request，生成 result，再回到正式主链完成渲染\n"
            "- Failure policy: 若 result 缺失/非法，Python 侧保持 fail-open，不把未精修结果冒充为已完成后处理\n"
            f"- Deduped Papers: {result.deduped_paper_count}\n"
            "当前未启动最终 HTML 渲染；等待 host Agent 完成 theme_postprocess_result.json。"
        )

    preview_note = (
        "\n- Note: This is not the full paper-search-pro workflow."
        if getattr(result, "report_mode", "") == "seed_preview"
        else ""
    )
    return (
        "✅ 专业调研报告已启动。\n\n"
        f"- Search Session: `{result.seed_session_id}`\n"
        f"- Report Mode: `{result.report_mode}`"
        f"{preview_note}\n"
        f"- Status: `{result.status}`\n"
        f"- PID: `{result.pid}`\n"
        f"- Link: [打开 HTML 报告]({result.file_url})\n"
        f"- Local Path: `{result.report_path}`\n"
        "- Tip: 如果链接在 Agent 代码编辑器内打开，请右键 HTML 文件标签，选择“在资源管理器中显示/打开”，再用浏览器打开原文件。\n"
        f"- Log: `{result.log_path}`\n"
        f"- Deduped Papers: {result.deduped_paper_count}\n"
        f"- Expanded Sources: {', '.join(result.expanded_sources) if result.expanded_sources else '(none)'}\n"
        "报告在后台生成；如文件暂未出现，请稍后查看 Report 路径或 Log。"
    )


@mcp.tool()
async def generate_recovery_report(
    sidecar_path: str = "",
    report_json: str = "",
    prefer: str = "auto",
    mode: str = "seed_preview",
) -> str:
    """Recover a SearchSession from sidecar/legacy materials and generate a report."""
    cfg = Config.load()
    resolved = resolve_report_recovery_session(
        sidecar=sidecar_path or None,
        report_json=report_json or None,
        prefer=prefer,
    )
    session = resolved.session
    save_session(session, Path(cfg.cache_dir))
    result = await asyncio.to_thread(
        report_bridge.start_report_from_session,
        session.session_id,
        config=cfg,
        mode=mode,
        display_query=session.display_query or session.recovered_label,
        open_report=True,
    )
    return (
        "✅ Recovery report started.\n\n"
        f"- Recovery Kind: `{resolved.decision.recovery_kind}`\n"
        f"- Search Session: `{result.seed_session_id}`\n"
        f"- Display Query: `{session.display_query or session.recovered_label}`\n"
        f"- Status: `{result.status}`\n"
        f"- Local Path: `{result.report_path}`\n"
    )


@mcp.tool()
async def get_theme_postprocess_request(
    search_session_id: str,
    mode: str = "seed_preview",
    display_query: str = "",
    language: str = "",
) -> str:
    """Prepare report artifacts and return the normalized theme-postprocess request payload."""

    try:
        result = await asyncio.to_thread(
            report_bridge.start_report_from_session,
            search_session_id,
            config=Config.load(),
            mode=mode,
            display_query=display_query,
            language=language,
            open_report=False,
        )
    except report_bridge.ReportBridgeConfigError as e:
        return (
            "⚠️ 主题后处理 request 生成失败。\n\n"
            f"原因：{e}\n"
            "请先确认报告桥接配置可用。"
        )
    except report_bridge.ReportBridgeError as e:
        return (
            "⚠️ 主题后处理 request 生成失败。\n\n"
            f"原因：{e}\n"
            "请检查 seed session 与 report adapter 主链。"
        )

    if getattr(result, "status", "") != "theme_postprocess_required":
        return (
            "⚠️ 当前报告不处于 theme_postprocess_required 状态。\n\n"
            f"- Search Session: `{result.seed_session_id}`\n"
            f"- Report Mode: `{result.report_mode}`\n"
            f"- Status: `{getattr(result, 'status', '')}`\n"
            "只有在 host Agent 需要接管主题后处理时，才会返回标准 request payload。"
        )

    request_path = Path(result.theme_postprocess_request_path)
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    return json.dumps(
        {
            "search_session_id": result.seed_session_id,
            "report_mode": result.report_mode,
            "status": result.status,
            "materialized_dir": result.materialized_dir,
            "request_path": result.theme_postprocess_request_path,
            "result_target_path": result.theme_postprocess_result_path,
            "payload": payload,
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
async def apply_theme_postprocess_result(
    search_session_id: str,
    result_json: str,
    mode: str = "seed_preview",
    display_query: str = "",
    language: str = "",
    open_report: bool = True,
) -> str:
    """Apply one host-Agent theme postprocess result and render the final HTML report."""

    try:
        payload = json.loads(result_json)
    except json.JSONDecodeError as e:
        return f"⚠️ theme postprocess result JSON 无法解析：{e}"

    try:
        result = await asyncio.to_thread(
            report_bridge.apply_theme_postprocess_and_render,
            search_session_id,
            result_payload=payload,
            config=Config.load(),
            mode=mode,
            display_query=display_query,
            language=language,
            open_report=open_report,
        )
    except report_bridge.ReportBridgeConfigError as e:
        return (
            "⚠️ 主题后处理回写失败。\n\n"
            f"原因：{e}\n"
            "请确认当前报告桥接仍指向内置 vpnsci seed adapter。"
        )
    except report_bridge.ReportBridgeError as e:
        return (
            "⚠️ 主题后处理回写后渲染失败。\n\n"
            f"原因：{e}\n"
            "请检查 result payload、materialized artifacts 与 paper-search-pro 运行时。"
        )

    return (
        "✅ 主题后处理结果已写回并完成渲染。\n\n"
        f"- Search Session: `{result.seed_session_id}`\n"
        f"- Report Mode: `{result.report_mode}`\n"
        f"- Status: `{result.status}`\n"
        f"- Request: `{result.theme_postprocess_request_path}`\n"
        f"- Result: `{result.theme_postprocess_result_path}`\n"
        f"- Link: [打开 HTML 报告]({result.file_url})\n"
        f"- Local Path: `{result.report_path}`\n"
        f"- Materialized Dir: `{result.materialized_dir}`\n"
        "- Tip: 如果链接在 Agent 代码编辑器内打开，请右键 HTML 文件标签，选择“在资源管理器中显示/打开”，再用浏览器打开原文件。"
    )


@mcp.tool()
async def get_paper_metadata(doi: str) -> str:
    """Get metadata for a paper by DOI from Semantic Scholar.

    Returns title, authors, year, abstract, citation count, and identifiers.
    Lighter than fetch_paper - does not download full text.

    Args:
        doi: The DOI of the paper (e.g. "10.1038/nphys1509").
    """
    config = Config.load()
    result = await asyncio.to_thread(
        semantic_scholar.get_paper,
        f"DOI:{doi}",
        api_key=config.semantic_scholar_api_key,
    )
    if result is None:
        return f"Paper not found for DOI: {doi}"

    lines = [f"# {result.title}"]
    if result.authors:
        lines.append(f"**Authors:** {', '.join(result.authors)}")
    if result.year:
        lines.append(f"**Year:** {result.year}")
    if result.journal:
        lines.append(f"**Journal:** {result.journal}")
    lines.append(f"**DOI:** {result.doi}")
    if result.arxiv_id:
        lines.append(f"**arXiv:** {result.arxiv_id}")
    lines.append(f"**Citations:** {result.citation_count}")
    if result.abstract:
        lines.append(f"\n## Abstract\n\n{result.abstract}")

    return "\n".join(lines)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
