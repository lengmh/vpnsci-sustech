"""MCP server exposing vpnsci-sustech tools for AI agents supporting MCP protocol."""

import asyncio
import logging
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import report_bridge
from .config import Config
from .fetcher import PaperFetcher
from .sources import publisher_search, search_mode, semantic_scholar, standard_search

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


@mcp.tool()
async def fetch_paper(identifier: str, format: str = "markdown") -> str:
    """Fetch an academic paper's full text by DOI or URL.

    Uses Open Access sources (Unpaywall, arXiv) first, then falls back
    to WebVPN/EZproxy for paywalled content. Results are cached locally.

    Args:
        identifier: DOI (e.g. "10.1038/nphys1509") or article URL.
        format: Output format - "markdown" (default), "json", or "text".
    """
    fetcher = _get_fetcher()
    if fetcher is None:
        return _SCHOOL_NOT_CONFIGURED

    paper = await asyncio.to_thread(fetcher.fetch, identifier)

    if not paper.full_text and not paper.abstract:
        return f"Could not extract full text for: {identifier}\nTitle: {paper.title}\nURL: {paper.url}"

    if format == "json":
        return paper.to_json()
    elif format == "text":
        return paper.to_text()
    else:
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
    if backend:
        try:
            results = await asyncio.to_thread(
                publisher_search.search,
                query,
                backend=backend,
                limit=limit,
            )
        except publisher_search.PublisherSearchBlockedError as e:
            return (
                f"⚠️ publisher-native search blocked for `{backend}`.\n\n"
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
                report_bridge.generate_report_from_session,
                session.session_id,
                config=config,
                mode="standard",
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

        return (
            "✅ 已按“专业调研”请求生成报告。\n\n"
            f"- Search Session: `{report.seed_session_id}`\n"
            f"- Report: `{report.report_path}`\n"
            f"- Deduped Papers: {report.deduped_paper_count}\n"
            f"- Expanded Sources: {', '.join(report.expanded_sources) if report.expanded_sources else '(none)'}\n"
            f"- Summary: {report.summary or '(none)'}"
        )


@mcp.tool()
async def generate_search_report(search_session_id: str, mode: str = "standard") -> str:
    """Generate an HTML research report from a saved search session.

    This is the explicit professional-research upgrade path. It uses the saved
    standard-search session as seed input for the configured paper-search-pro
    bridge. It is not called by normal search automatically.

    Args:
        search_session_id: Search session id returned by search_papers.
        mode: Report mode passed to the bridge. Default: standard.
    """
    try:
        result = await asyncio.to_thread(
            report_bridge.generate_report_from_session,
            search_session_id,
            config=Config.load(),
            mode=mode,
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

    return (
        "✅ 专业调研报告已生成。\n\n"
        f"- Search Session: `{result.seed_session_id}`\n"
        f"- Report: `{result.report_path}`\n"
        f"- Deduped Papers: {result.deduped_paper_count}\n"
        f"- Expanded Sources: {', '.join(result.expanded_sources) if result.expanded_sources else '(none)'}\n"
        f"- Summary: {result.summary or '(none)'}"
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
