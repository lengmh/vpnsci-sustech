"""CNKI metadata/session probe and gated artifact helpers.

This module does not automate login or captcha handling. Live browser access is
limited to explicit visible-browser smoke paths after caller confirmation.
"""

from __future__ import annotations

import base64
import json
import re
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from uuid import uuid4

from bs4 import BeautifulSoup

from ..config import Config
from ..extractors import pdf_extractor
from ..file_naming import build_artifact_stem, reserve_unique_path
from ..download_workflows import DownloadWorkflowSidecar, write_download_workflow_sidecar
from ..models import Artifact, Paper
from ..site_policy import CNKI_MAX_DOWNLOADS_PER_RUN, CNKI_MIN_INTERVAL_SECONDS
from .search_cache import SearchError, SearchSession, new_session_id, save_session
from .search_models import SearchHit, build_hit_key


CNKI_DOWNLOAD_EXTENSIONS = {"pdf", "caj", "cajx", "nh", "kdh"}
CNKI_PARTIAL_SUFFIXES = (".crdownload", ".tmp")
CNKI_ALLOWED_HOST_SUFFIXES = ("cnki.net", "oversea.cnki.net")
CNKI_BLOCKED_HOSTS = {"fsso.cnki.net", "login.cnki.net"}
CNKI_SMOKE_MAX_RESULTS = 3
CNKI_DOWNLOAD_TIMEOUT_SECONDS = 45
CNKI_DEFAULT_RECOVERED_LABEL = "CNKI 下载结果集合"


@dataclass
class DownloadedArtifact:
    content: bytes
    path: Path
    format: str
    source_url: str = ""
    metadata: Paper | None = None
    note: str = ""


@dataclass
class CNKIBatchItem:
    detail_url: str
    title: str = ""
    first_author: str = ""
    cnki_id: str = ""
    source_url: str = ""


@dataclass
class CNKIBatchEntry:
    item: CNKIBatchItem
    status: str = "pending"
    artifact_path: str = ""
    format: str = ""
    note: str = ""
    error: str = ""
    attempts: int = 0
    started_at: str = ""
    finished_at: str = ""


@dataclass
class CNKIBatchResult:
    status: str
    state_path: Path
    sidecar_path: Path | None = None
    entries: list[CNKIBatchEntry] = field(default_factory=list)
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    pending: int = 0
    stopped_reason: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class CNKIVisibleSmokeResult:
    status: str
    dry_run: bool
    mode: str
    query: str = ""
    detail_url: str = ""
    search_url: str = ""
    limit: int = 1
    page_state: str = ""
    hits: list[SearchHit] = field(default_factory=list)
    paper: Paper | None = None
    warnings: list[str] = field(default_factory=list)
    next_action: str = ""


@dataclass
class CNKIDetailResult:
    status: str
    url_or_id: str = ""
    url: str = ""
    page_state: str = ""
    paper: Paper | None = None
    warnings: list[str] = field(default_factory=list)
    next_action: str = ""


def detect_cnki_page_state(html: str, url: str = "") -> str:
    """Classify a CNKI page snapshot for conservative automation flow."""

    lowered = f"{html or ''} {url or ''}".lower()
    url_lower = (url or "").lower()
    is_detail_url = "kcms2/article/abstract" in url_lower or "kcms/detail" in url_lower
    has_detail = any(signal in lowered for signal in ["kcms2/article/abstract", "chdivsummary", "class='title'", 'class="title"'])
    has_download = any(signal in lowered for signal in ["bar/download", "/download", "pdf下载", "caj下载", "下载"])
    has_search_results = any(signal in lowered for signal in ["result-table-list", "result-table", "defaultresult", "search-result"])
    if is_detail_url and has_detail:
        return "detail_page"
    if has_search_results:
        return "search_results"
    if has_detail and has_download:
        return "detail_page"
    if any(signal in lowered for signal in ["验证码", "滑块", "安全验证", "captcha"]):
        return "captcha_required"
    if any(signal in lowered for signal in ["统一身份认证", "用户登录", "login.cnki", "fsso.cnki"]):
        return "manual_login_required"
    if has_detail:
        return "detail_page"
    return "unknown"


def extract_cnki_identifiers(url: str) -> dict[str, str]:
    """Extract common CNKI identifiers from a detail/download URL."""

    parsed = urlparse(url or "")
    query = parse_qs(parsed.query)
    keys = ["filename", "dbname", "dbcode", "dbsource"]
    result = {}
    for key in keys:
        values = query.get(key) or query.get(key.upper()) or []
        if values:
            result[key] = values[0]
    return result


def is_cnki_url(url: str) -> bool:
    """Return True only for CNKI hosts accepted by the explicit CNKI path."""

    host = (urlparse(url or "").hostname or "").lower()
    if host in CNKI_BLOCKED_HOSTS:
        return False
    return host == "cnki.net" or host.endswith(".cnki.net") or host == "oversea.cnki.net" or host.endswith(".oversea.cnki.net")


def build_cnki_search_url(query: str, *, search_type: str = "theme") -> str:
    """Build the visible-browser CNKI search URL used by smoke runs."""

    params = {"kw": query or ""}
    if search_type:
        params["searchType"] = search_type
    return "https://kns.cnki.net/kns8s/defaultresult/index?" + urlencode(params)


def normalize_cnki_detail_reference(url_or_id: str) -> tuple[str, str]:
    """Normalize a CNKI detail URL or filename-like identifier without network."""

    value = (url_or_id or "").strip()
    if not value:
        return "missing_target", ""
    parsed = urlparse(value)
    if parsed.scheme and parsed.netloc:
        if not is_cnki_url(value):
            return "invalid_url", ""
        return "ok", value
    return "ok", "https://kns.cnki.net/kcms2/article/abstract?" + urlencode({"filename": value})


def get_cnki_detail(
    url_or_id: str = "",
    *,
    html: str = "",
    html_file: str | Path = "",
    base_url: str = "https://kns.cnki.net/",
) -> CNKIDetailResult:
    """Parse CNKI detail metadata from supplied HTML/page-source.

    This helper intentionally does not access CNKI. Provide ``html`` or
    ``html_file`` captured from a user-managed browser or visible smoke path.
    """

    ref_status, normalized_url = normalize_cnki_detail_reference(url_or_id)
    if ref_status == "invalid_url":
        return CNKIDetailResult(
            status="invalid_url",
            url_or_id=url_or_id,
            warnings=["url_or_id 不是允许的 CNKI 域名。"],
            next_action="只允许 CNKI detail URL，或传入 filename/CNKI ID。",
        )
    if html_file:
        html = Path(html_file).read_text(encoding="utf-8-sig")
    if not html:
        return CNKIDetailResult(
            status="live_access_not_enabled",
            url_or_id=url_or_id,
            url=normalized_url,
            warnings=["未提供 HTML；本工具不会直接访问 CNKI。"],
            next_action="提供 html/html_file，或先运行 cnki-smoke dry-run/visible-browser smoke 获取页面快照。",
        )

    page_url = normalized_url or base_url
    state = detect_cnki_page_state(html, page_url)
    if state in {"manual_login_required", "captcha_required"}:
        return CNKIDetailResult(
            status=state,
            url_or_id=url_or_id,
            url=page_url,
            page_state=state,
            warnings=[f"CNKI returned {state}; visible-browser user action is required."],
            next_action="需要用户在可见浏览器内手动完成登录/验证码；工具不会绕过。",
        )

    paper = parse_cnki_detail(html, url=page_url)
    if not (paper.title or paper.abstract or paper.authors):
        return CNKIDetailResult(
            status="no_detail_found",
            url_or_id=url_or_id,
            url=page_url,
            page_state=state,
            warnings=["未能从 HTML 中解析出详情页元数据。"],
            next_action="保存脱敏 page source 后补充 fixture/选择器。",
        )

    return CNKIDetailResult(
        status="ok",
        url_or_id=url_or_id,
        url=page_url,
        page_state=state,
        paper=paper,
    )


def _bounded_smoke_limit(limit: int) -> tuple[int, list[str]]:
    warnings: list[str] = []
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = 1
        warnings.append("limit 无效，已按 1 处理。")
    if value < 1:
        warnings.append("CNKI smoke 最小 limit 为 1，已按 1 处理。")
        value = 1
    if value > CNKI_SMOKE_MAX_RESULTS:
        warnings.append(f"CNKI smoke 最多解析 {CNKI_SMOKE_MAX_RESULTS} 条结果，已截断。")
        value = CNKI_SMOKE_MAX_RESULTS
    return value, warnings


def _build_smoke_result(
    *,
    status: str,
    dry_run: bool,
    mode: str,
    query: str = "",
    detail_url: str = "",
    search_url: str = "",
    limit: int = 1,
    warnings: list[str] | None = None,
    next_action: str = "",
) -> CNKIVisibleSmokeResult:
    return CNKIVisibleSmokeResult(
        status=status,
        dry_run=dry_run,
        mode=mode,
        query=query,
        detail_url=detail_url,
        search_url=search_url,
        limit=limit,
        warnings=warnings or [],
        next_action=next_action,
    )


def run_visible_browser_smoke(
    *,
    query: str = "",
    detail_url: str = "",
    limit: int = 1,
    mode: str = "managed",
    dry_run: bool = True,
    confirm_live_access: bool = False,
    search_type: str = "theme",
    debug_port: int = 9222,
    config: Config | None = None,
    driver_factory=None,
) -> CNKIVisibleSmokeResult:
    """Plan or run a tightly gated visible-browser CNKI smoke probe.

    Dry-run is the default and never launches a browser. Live execution requires
    confirm_live_access=True and is limited to one search/detail page snapshot;
    it does not download files, submit credentials, or handle captcha.
    """

    mode = (mode or "managed").strip().lower()
    bounded_limit, warnings = _bounded_smoke_limit(limit)
    if mode not in {"managed", "attach"}:
        return _build_smoke_result(
            status="invalid_mode",
            dry_run=dry_run,
            mode=mode,
            query=query,
            detail_url=detail_url,
            limit=bounded_limit,
            warnings=[*warnings, "mode 只能是 managed 或 attach。"],
            next_action="改用 mode=managed，或由用户自行启动 Chrome debug session 后使用 mode=attach。",
        )

    if detail_url and not is_cnki_url(detail_url):
        return _build_smoke_result(
            status="invalid_url",
            dry_run=dry_run,
            mode=mode,
            query=query,
            detail_url=detail_url,
            limit=bounded_limit,
            warnings=[*warnings, "detail_url 不是允许的 CNKI 域名。"],
            next_action="只允许 kns.cnki.net / cnki.net / oversea.cnki.net 等 CNKI URL。",
        )

    search_url = build_cnki_search_url(query, search_type=search_type) if query else ""
    target_url = detail_url or search_url
    if not target_url:
        return _build_smoke_result(
            status="missing_target",
            dry_run=dry_run,
            mode=mode,
            limit=bounded_limit,
            warnings=[*warnings, "需要 query 或 detail_url。"],
            next_action="传入 query 做搜索页 smoke，或传入 detail_url 做详情页 smoke。",
        )

    safety_warnings = [
        "不会下载文件。",
        "不会提交账号密码。",
        "不会绕过验证码。",
        f"站点限速基线：至少 {CNKI_MIN_INTERVAL_SECONDS:.0f}s；单次运行下载上限 {CNKI_MAX_DOWNLOADS_PER_RUN}，本 smoke 下载数为 0。",
    ]
    warnings = [*warnings, *safety_warnings]
    if dry_run:
        return _build_smoke_result(
            status="dry_run",
            dry_run=True,
            mode=mode,
            query=query,
            detail_url=detail_url,
            search_url=search_url,
            limit=bounded_limit,
            warnings=warnings,
            next_action="如需真实 visible-browser smoke，用户需明确确认后设置 dry_run=False 且 confirm_live_access=True。",
        )

    if not confirm_live_access:
        return _build_smoke_result(
            status="confirmation_required",
            dry_run=False,
            mode=mode,
            query=query,
            detail_url=detail_url,
            search_url=search_url,
            limit=bounded_limit,
            warnings=warnings,
            next_action="真实 CNKI 访问需要用户明确确认；确认前不会打开浏览器或访问站点。",
        )

    cfg = config or Config.load()
    driver = _launch_cnki_visible_driver(cfg, mode=mode, debug_port=debug_port, driver_factory=driver_factory)
    try:
        driver.get(target_url)
        current_url = getattr(driver, "current_url", target_url)
        html = getattr(driver, "page_source", "") or ""
        state = detect_cnki_page_state(html, current_url)
        result = CNKIVisibleSmokeResult(
            status=state,
            dry_run=False,
            mode=mode,
            query=query,
            detail_url=detail_url,
            search_url=search_url,
            limit=bounded_limit,
            page_state=state,
            warnings=warnings,
        )
        if state == "search_results":
            result.hits = parse_cnki_search_results(html, base_url=current_url)[:bounded_limit]
            result.next_action = "已完成搜索页快照解析；真实下载仍需单独显式触发。"
        elif state == "detail_page":
            result.paper = parse_cnki_detail(html, url=current_url)
            result.next_action = "已完成详情页快照解析；真实下载仍需单独显式触发。"
        elif state in {"manual_login_required", "captcha_required"}:
            result.next_action = "需要用户在可见浏览器内手动完成登录/验证码；工具不会绕过。"
        else:
            result.next_action = "页面状态未知；请保存脱敏 page source 后补 fixture/选择器。"
        return result
    finally:
        quit_fn = getattr(driver, "quit", None)
        if callable(quit_fn):
            quit_fn()


def _launch_cnki_visible_driver(
    config: Config,
    *,
    mode: str,
    debug_port: int = 9222,
    driver_factory=None,
    download_dir: str | Path | None = None,
):
    if driver_factory is not None:
        return driver_factory()

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    opts = Options()
    opts.add_argument("--start-maximized")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    if download_dir is not None:
        opts.add_experimental_option(
            "prefs",
            {
                "download.default_directory": str(Path(download_dir).resolve()),
                "download.prompt_for_download": False,
                "plugins.always_open_pdf_externally": True,
            },
        )
    if mode == "attach":
        opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
    else:
        profile_dir = Path(config.chrome_profile_dir)
        profile_dir.mkdir(parents=True, exist_ok=True)
        opts.add_argument(f"--user-data-dir={profile_dir}")
    return webdriver.Chrome(options=opts)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _split_authors(text: str) -> list[str]:
    value = _clean_text(text)
    if not value:
        return []
    parts = re.split(r"[;；,，\s]+", value)
    return [p for p in (_clean_text(p) for p in parts) if p and "@" not in p]


def _year_from_text(text: str) -> int | None:
    match = re.search(r"(19|20)\d{2}", text or "")
    return int(match.group(0)) if match else None


def parse_cnki_search_results(html: str, *, base_url: str = "https://kns.cnki.net/") -> list[SearchHit]:
    """Parse CNKI search result HTML into unified SearchHit objects."""

    soup = BeautifulSoup(html or "", "lxml")
    rows = soup.select("table.result-table-list tr, .result-table-list tr, .result-table tr, .search-result")
    hits: list[SearchHit] = []
    for row in rows:
        title_link = row.select_one(".name a[href], a[href*='kcms2/article'], a[href*='KCMS/detail']")
        if not title_link:
            continue
        title = _clean_text(title_link.get_text(" ", strip=True))
        if not title:
            continue
        detail_url = urljoin(base_url, title_link.get("href", ""))
        ids = extract_cnki_identifiers(detail_url)
        author_text = _clean_text((row.select_one(".author") or row.select_one("td.author") or row.select_one("[data-field='author']") or row).get_text(" ", strip=True))
        source_el = row.select_one(".source, td.source, [data-field='source']")
        date_el = row.select_one(".date, td.date, [data-field='date']")
        download_el = row.select_one("a[href*='download'], a[href*='Download']")
        hit = SearchHit(
            title=title,
            authors=_split_authors(author_text.replace(title, "")),
            journal=_clean_text(source_el.get_text(" ", strip=True)) if source_el else "",
            year=_year_from_text(date_el.get_text(" ", strip=True) if date_el else row.get_text(" ", strip=True)),
            url=detail_url,
            cnki_id=ids.get("filename", ""),
            source_url=detail_url,
            download_format="pdf" if download_el and "pdf" in download_el.get_text(" ", strip=True).lower() else "",
            source="cnki",
            backend="cnki",
            sources=["cnki"],
        )
        hits.append(hit)
    return hits


def parse_cnki_detail(html: str, *, url: str = "") -> Paper:
    """Parse CNKI detail HTML into a Paper object."""

    soup = BeautifulSoup(html or "", "lxml")
    title = _extract_detail_title(soup)

    author_el = soup.select_one("#authorpart, .author, .authors")
    authors = _split_authors(author_el.get_text(" ", strip=True) if author_el else "")

    source_text = _clean_text(" ".join(
        el.get_text(" ", strip=True)
        for el in soup.select(".sourinfo, .top-tip, .source, .journal")
    ))
    if not source_text:
        source_text = soup.get_text(" ", strip=True)
    journal = ""
    if source_text:
        journal = re.sub(r"(19|20)\d{2}.*$", "", source_text).strip()

    abstract_el = soup.select_one("#ChDivSummary, .abstract, .summary")
    abstract = _clean_text(abstract_el.get_text(" ", strip=True) if abstract_el else "")
    abstract = re.sub(r"^摘要[:：]\s*", "", abstract)

    paper = Paper(
        title=title,
        authors=authors,
        journal=journal,
        year=_year_from_text(source_text),
        abstract=abstract,
        source="cnki",
        url=url,
    )
    ids = extract_cnki_identifiers(url)
    setattr(paper, "cnki_id", ids.get("filename", ""))
    return paper


def _extract_detail_title(soup: BeautifulSoup) -> str:
    """Extract the article title while avoiding CNKI help/recommendation widgets."""

    title_tag = soup.select_one("title")
    if title_tag:
        title = _clean_detail_title(title_tag.get_text(" ", strip=True))
        if title and title not in {"中国知网", "使用帮助"}:
            return title

    for selector in ("h1.title", ".wx-tit h1", "#title", "h1"):
        title_el = soup.select_one(selector)
        title = _clean_detail_title(title_el.get_text(" ", strip=True) if title_el else "")
        if title and title not in {"使用帮助", "自动登录"}:
            return title

    title_el = soup.select_one(".title")
    return _clean_detail_title(title_el.get_text(" ", strip=True) if title_el else "")


def _clean_detail_title(title: str) -> str:
    value = _clean_text(title)
    value = re.sub(r"\s*[-_—–]\s*中国知网\s*$", "", value)
    value = re.sub(r"\s*附视频\s*$", "", value)
    return _clean_text(value)


def find_cnki_download_url(html: str, *, base_url: str, prefer: str = "pdf") -> tuple[str, str]:
    """Find a conservative CNKI download URL from a detail page snapshot.

    Returns ``(url, format)``. It never guesses off-page endpoints; only links
    present in the current page are considered.
    """

    soup = BeautifulSoup(html or "", "lxml")
    preferred = (prefer or "pdf").strip().lower().lstrip(".")
    order: list[str] = []
    if preferred in CNKI_DOWNLOAD_EXTENSIONS:
        order.append(preferred)
    for ext in ["pdf", "caj", "cajx", "nh", "kdh"]:
        if ext not in order:
            order.append(ext)

    candidates: list[tuple[str, str, int, str]] = []
    for link in soup.select("a[href]"):
        href = link.get("href", "")
        text = _clean_text(link.get_text(" ", strip=True)).lower()
        element_id = (link.get("id") or "").lower()
        class_text = " ".join(link.get("class") or []).lower()
        marker = f"{href} {text} {element_id} {class_text}".lower()
        if not any(signal in marker for signal in ["download", "down", "下载", "pdf", "caj", "cajx", "nh", "kdh"]):
            continue
        if "but-ad" in class_text or "/ads/" in href.lower():
            continue
        fmt = ""
        priority = 20
        if "pdfdown" in element_id or "pdf下载" in text or "pdf 下载" in text:
            fmt = "pdf"
            priority = 0
        elif "cajdown" in element_id or "caj下载" in text or "caj 下载" in text:
            fmt = "caj"
            priority = 0
        elif "cajx下载" in text or "cajx 下载" in text:
            fmt = "cajx"
            priority = 0
        else:
            parsed_href = urlparse(href)
            href_path = parsed_href.path.lower()
            href_query = parse_qs(parsed_href.query)
            query_format = " ".join(v for values in href_query.values() for v in values).lower()
            for ext in ["pdf", "cajx", "caj", "nh", "kdh"]:
                if re.search(rf"(^|[=&._/-]){re.escape(ext)}($|[=&._/-])", query_format) or href_path.endswith(f".{ext}"):
                    fmt = ext
                    priority = 5
                    break
        if not fmt:
            continue
        candidates.append((urljoin(base_url, href), fmt, priority, marker))

    for fmt in order:
        for url, candidate_fmt, _priority, _marker in sorted(candidates, key=lambda item: item[2]):
            if candidate_fmt == fmt:
                return url, candidate_fmt

    return "", ""


def search_cnki_from_html(
    query: str,
    html: str,
    *,
    limit: int = 10,
    cache_dir: str | Path | None = None,
    base_url: str = "https://kns.cnki.net/",
) -> SearchSession:
    """Build and persist a CNKI SearchSession from supplied HTML fixture/page source."""

    state = detect_cnki_page_state(html, base_url)
    errors: list[SearchError] = []
    hits: list[SearchHit] = []
    if state in {"manual_login_required", "captcha_required"}:
        errors.append(
            SearchError(
                source="cnki",
                code=state,
                message=f"CNKI returned {state}; visible-browser user action is required.",
            )
        )
    else:
        hits = parse_cnki_search_results(html, base_url=base_url)[:limit]

    session = SearchSession(
        session_id=new_session_id(),
        query=query,
        origin={
            "engine": "cnki",
            "kind": "html_import",
            "capture_source": "user_html",
        },
        display_query=query,
        filters={"backend": "cnki", "limit": limit},
        hits=hits,
        source_summary={"cnki": len(hits)},
        errors=errors,
    )
    if cache_dir is not None:
        save_session(session, Path(cache_dir))
    return session


def search_cnki_from_html_file(
    query: str,
    html_file: str | Path,
    *,
    limit: int = 10,
    cache_dir: str | Path | None = None,
    base_url: str = "https://kns.cnki.net/",
) -> SearchSession:
    """Build and persist a CNKI SearchSession from a captured HTML file."""

    html = Path(html_file).read_text(encoding="utf-8-sig")
    return search_cnki_from_html(
        query,
        html,
        limit=limit,
        cache_dir=cache_dir,
        base_url=base_url,
    )


def search_cnki(query: str, limit: int = 10, search_type: str = "theme", *, config=None) -> SearchSession:
    """Explicit CNKI search entry.

    Network/browser execution is intentionally not enabled in this stage. Use
    search_cnki_from_html() for fixture/page-source parsing, or continue with
    the planned visible-browser probe before enabling live access.
    """

    cache_dir = Path(getattr(config, "cache_dir", "")) if config is not None and getattr(config, "cache_dir", "") else None
    session = SearchSession(
        session_id=new_session_id(),
        query=query,
        origin={
            "engine": "cnki",
            "kind": "gated_request",
            "route_reason": "explicit_backend",
        },
        display_query=query,
        filters={"backend": "cnki", "limit": limit, "search_type": search_type},
        hits=[],
        source_summary={"cnki": 0},
        errors=[
            SearchError(
                source="cnki",
                code="live_access_not_enabled",
                message="CNKI live search is gated; provide captured HTML or run the visible-browser probe phase first.",
            )
        ],
    )
    if cache_dir is not None:
        save_session(session, cache_dir)
    return session


def wait_for_cnki_download(
    download_dir: str | Path,
    *,
    timeout: int = 45,
    extensions: set[str] | None = None,
    before: dict[Path, tuple[float, int]] | set[Path] | None = None,
) -> DownloadedArtifact | None:
    """Wait for a CNKI browser download to finish.

    Supports PDF and CNKI source formats. The caller controls when a browser is
    opened; this helper only observes a local directory and never contacts CNKI.
    """

    allowed = {ext.lower().lstrip(".") for ext in (extensions or CNKI_DOWNLOAD_EXTENSIONS)}
    before_snapshot = _normalize_cnki_download_snapshot(before)
    directory = Path(download_dir)
    deadline = time.time() + max(timeout, 0)
    while True:
        files = [p for p in directory.iterdir() if p.is_file()]
        partial = [
            p for p in files
            if p.name.lower().endswith(CNKI_PARTIAL_SUFFIXES)
        ]
        complete = [
            p for p in files
            if _cnki_file_is_new_or_changed(p, before_snapshot)
            and p.suffix.lower().lstrip(".") in allowed
            and p.stat().st_size > 0
        ]
        if complete and not partial:
            file_path = max(complete, key=lambda p: p.stat().st_mtime)
            return DownloadedArtifact(
                content=file_path.read_bytes(),
                path=file_path,
                format=file_path.suffix.lower().lstrip("."),
            )
        if time.time() >= deadline:
            return None
        time.sleep(1)


def wait_for_cnki_download_after_manual_captcha(
    driver,
    download_dir: str | Path,
    *,
    timeout: int = 45,
    extensions: set[str] | None = None,
    before: dict[Path, tuple[float, int]] | set[Path] | None = None,
) -> DownloadedArtifact | None:
    """Wait while the user completes a visible CNKI captcha, then resume.

    This helper does not solve or bypass captcha. It only observes the visible
    browser and local download directory after the click has already opened a
    CNKI/bar verification page.
    """

    allowed = {ext.lower().lstrip(".") for ext in (extensions or CNKI_DOWNLOAD_EXTENSIONS)}
    before_snapshot = _normalize_cnki_download_snapshot(before)
    directory = Path(download_dir)
    deadline = time.time() + max(timeout, 0)
    while True:
        downloaded = _latest_completed_cnki_download(directory, allowed=allowed, before_snapshot=before_snapshot)
        if downloaded is not None:
            return downloaded

        current_url = getattr(driver, "current_url", "") or ""
        html = getattr(driver, "page_source", "") or ""
        if "verifysuccess" in current_url.lower() or "verifysuccess" in html.lower():
            # CNKI/bar often starts the browser download immediately after the
            # success page appears. Keep observing the directory until timeout.
            pass
        elif not _cnki_page_looks_like_captcha_or_verify(current_url, html):
            # The user may have completed verification and been redirected back
            # to the previous page. Keep observing local download state.
            pass

        if time.time() >= deadline:
            return None

        refresh = getattr(driver, "refresh", None)
        if callable(refresh):
            try:
                refresh()
            except Exception:
                pass
        time.sleep(1)


def snapshot_cnki_download_dir(download_dir: str | Path) -> dict[Path, tuple[float, int]]:
    """Snapshot file identity for detecting new or overwritten downloads."""

    directory = Path(download_dir)
    if not directory.exists():
        return {}
    snapshot: dict[Path, tuple[float, int]] = {}
    for path in directory.iterdir():
        if not path.is_file():
            continue
        stat = path.stat()
        snapshot[path.resolve()] = (stat.st_mtime, stat.st_size)
    return snapshot


def _normalize_cnki_download_snapshot(
    before: dict[Path, tuple[float, int]] | set[Path] | None,
) -> dict[Path, tuple[float, int]]:
    if before is None:
        return {}
    if isinstance(before, dict):
        return {Path(path).resolve(): value for path, value in before.items()}
    return {Path(path).resolve(): (-1.0, -1) for path in before}


def _cnki_file_is_new_or_changed(path: Path, before: dict[Path, tuple[float, int]]) -> bool:
    previous = before.get(path.resolve())
    if previous is None:
        return True
    stat = path.stat()
    return (stat.st_mtime, stat.st_size) != previous


def _latest_completed_cnki_download(
    directory: Path,
    *,
    allowed: set[str],
    before_snapshot: dict[Path, tuple[float, int]],
) -> DownloadedArtifact | None:
    if not directory.exists():
        return None
    files = [p for p in directory.iterdir() if p.is_file()]
    partial = [
        p for p in files
        if p.name.lower().endswith(CNKI_PARTIAL_SUFFIXES)
    ]
    complete = [
        p for p in files
        if _cnki_file_is_new_or_changed(p, before_snapshot)
        and p.suffix.lower().lstrip(".") in allowed
        and p.stat().st_size > 0
    ]
    if complete and not partial:
        file_path = max(complete, key=lambda p: p.stat().st_mtime)
        return DownloadedArtifact(
            content=file_path.read_bytes(),
            path=file_path,
            format=file_path.suffix.lower().lstrip("."),
        )
    return None


def _cnki_driver_is_captcha_or_verify(driver) -> bool:
    current_url = getattr(driver, "current_url", "") or ""
    html = getattr(driver, "page_source", "") or ""
    return _cnki_page_looks_like_captcha_or_verify(current_url, html)


def _cnki_page_looks_like_captcha_or_verify(url: str, html: str) -> bool:
    lowered = f"{url or ''} {html or ''}".lower()
    return any(
        signal in lowered
        for signal in [
            "bar.cnki.net/bar/verify",
            "captcha",
            "验证码",
            "滑块",
            "拼图",
            "安全验证",
            "tencent-captcha",
        ]
    )


def save_cnki_downloaded_artifact(
    paper: Paper,
    downloaded: DownloadedArtifact,
    *,
    config: Config | None = None,
    filename_policy: str = "",
    filename_template: str = "",
) -> Artifact:
    """Save a CNKI downloaded artifact through the shared filename policy."""

    cfg = config or Config.load()
    policy = filename_policy or getattr(cfg, "paper_filename_policy", "title_author") or "title_author"
    template = filename_template or getattr(cfg, "paper_filename_template", "") or ""
    max_length = int(getattr(cfg, "paper_filename_max_length", 180) or 180)
    collision = getattr(cfg, "paper_filename_collision", "hash") or "hash"
    ext = (downloaded.format or downloaded.path.suffix).lower().lstrip(".") or "bin"
    stem = build_artifact_stem(
        paper,
        policy=policy,
        template=template,
        max_length=max_length,
    )
    path = reserve_unique_path(
        cfg.output_dir,
        stem=stem,
        ext=ext,
        collision_key=getattr(paper, "cnki_id", "") or downloaded.source_url or paper.url or stem,
        collision=collision,
        overwrite=False,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(downloaded.content)

    is_pdf = ext == "pdf"
    extracted_text = ""
    if is_pdf:
        extracted_text = pdf_extractor.extract_from_bytes(downloaded.content)
        if extracted_text:
            paper.full_text = extracted_text
            paper.figures = pdf_extractor.extract_figures_from_text(extracted_text)
    base_note = (
        "" if extracted_text
        else "CNKI PDF 已保存，但未能提取全文。" if is_pdf
        else "CNKI 原文已保存，但当前未解析全文。"
    )
    note = _append_note(base_note, downloaded.note)

    artifact = Artifact(
        path=str(path),
        format=ext,
        kind="fulltext" if is_pdf else "source_file",
        source_url=downloaded.source_url,
        text_extracted=bool(extracted_text) if is_pdf else False,
        note=note,
    )
    paper.artifacts = [
        existing for existing in paper.artifacts
        if not (existing.path == artifact.path and existing.format == artifact.format)
    ]
    paper.artifacts.append(artifact)
    if is_pdf:
        paper.pdf_path = artifact.path
    elif ext in {"caj", "cajx"}:
        converted = maybe_convert_cnki_source_to_pdf(paper, artifact, config=cfg)
        if converted is not None:
            paper.artifacts.append(converted)
            paper.pdf_path = converted.path
    return artifact


def maybe_convert_cnki_source_to_pdf(
    paper: Paper,
    source_artifact: Artifact,
    *,
    config: Config | None = None,
) -> Artifact | None:
    """Optionally convert a CNKI CAJ/CAJX source file to PDF via external command.

    Conversion is disabled by default and never installs or vendors converters.
    """

    cfg = config or Config.load()
    if not getattr(cfg, "cnki_convert_caj_to_pdf", False):
        return None
    command_template = getattr(cfg, "cnki_caj_converter_command", "") or ""
    if not command_template:
        source_artifact.note = _append_note(source_artifact.note, "CAJ 转 PDF 已启用，但未配置转换命令。")
        return None

    input_path = Path(source_artifact.path)
    if input_path.suffix.lower().lstrip(".") not in {"caj", "cajx"}:
        return None
    output_path = input_path.with_suffix(".pdf")
    command_args = _converter_command_args(command_template, input_path=input_path, output_path=output_path)
    if command_args is None:
        source_artifact.note = _append_note(source_artifact.note, "CAJ 转 PDF 未执行：转换命令必须包含 {input} 和 {output}。")
        return None

    try:
        completed = subprocess.run(
            command_args,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as e:
        source_artifact.note = _append_note(source_artifact.note, f"CAJ 转 PDF 未执行：{e}")
        return None

    if completed.returncode != 0 or not output_path.exists() or output_path.stat().st_size <= 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        note = "CAJ 转 PDF 失败；已保留原始文件。"
        if detail:
            note += f" {detail[:200]}"
        source_artifact.note = _append_note(source_artifact.note, note)
        return None

    pdf_bytes = output_path.read_bytes()
    text = pdf_extractor.extract_from_bytes(pdf_bytes)
    if text:
        paper.full_text = text
        paper.figures = pdf_extractor.extract_figures_from_text(text)

    return Artifact(
        path=str(output_path),
        format="pdf",
        kind="converted_pdf",
        source_url=source_artifact.source_url,
        text_extracted=bool(text),
        note="" if text else "CAJ 已转换为 PDF，但未能提取全文。",
    )


def _converter_command_args(command_template: str, *, input_path: Path, output_path: Path) -> list[str] | None:
    input_token = "__VPNSCI_CAJ_INPUT__"
    output_token = "__VPNSCI_CAJ_OUTPUT__"
    command = command_template.format(input=input_token, output=output_token)
    args = shlex.split(command)
    if input_token not in args or output_token not in args:
        return None
    return [
        str(input_path) if arg == input_token else str(output_path) if arg == output_token else arg
        for arg in args
    ]


def _append_note(current: str, extra: str) -> str:
    current = (current or "").strip()
    extra = (extra or "").strip()
    if not current:
        return extra
    if not extra:
        return current
    return f"{current} {extra}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cnki_batch_state_dir(cache_dir: str | Path) -> Path:
    return Path(cache_dir) / "cnki" / "batch"


def _default_cnki_batch_state_path(cache_dir: str | Path) -> Path:
    directory = _cnki_batch_state_dir(cache_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"cnki-batch-{uuid4().hex[:12]}.json"


def _serialize_cnki_batch_entry(entry: CNKIBatchEntry) -> dict:
    return {
        "item": asdict(entry.item),
        "status": entry.status,
        "artifact_path": entry.artifact_path,
        "format": entry.format,
        "note": entry.note,
        "error": entry.error,
        "attempts": entry.attempts,
        "started_at": entry.started_at,
        "finished_at": entry.finished_at,
    }


def _write_cnki_batch_state(path: Path, entries: list[CNKIBatchEntry], *, status: str = "running", stopped_reason: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "status": status,
        "stopped_reason": stopped_reason,
        "updated_at": _utc_now_iso(),
        "entries": [_serialize_cnki_batch_entry(entry) for entry in entries],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_cnki_batch_state(path: str | Path) -> list[CNKIBatchEntry]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entries: list[CNKIBatchEntry] = []
    for raw in data.get("entries", []):
        item_raw = raw.get("item") or {}
        item = CNKIBatchItem(
            detail_url=item_raw.get("detail_url", ""),
            title=item_raw.get("title", ""),
            first_author=item_raw.get("first_author", ""),
            cnki_id=item_raw.get("cnki_id", ""),
            source_url=item_raw.get("source_url", ""),
        )
        entries.append(
            CNKIBatchEntry(
                item=item,
                status=raw.get("status") or "pending",
                artifact_path=raw.get("artifact_path") or "",
                format=raw.get("format") or "",
                note=raw.get("note") or "",
                error=raw.get("error") or "",
                attempts=int(raw.get("attempts") or 0),
                started_at=raw.get("started_at") or "",
                finished_at=raw.get("finished_at") or "",
            )
        )
    return entries


def _cnki_batch_status(entries: list[CNKIBatchEntry], stopped_reason: str = "") -> str:
    if stopped_reason:
        return "stopped"
    if any(entry.status == "pending" for entry in entries):
        return "partial"
    if any(entry.status == "failed" for entry in entries):
        return "completed_with_failures"
    return "completed"


def _sidecar_item_from_batch_entry(entry: CNKIBatchEntry) -> dict:
    item = entry.item
    identifiers = extract_cnki_identifiers(item.detail_url or item.source_url)
    cnki_id = item.cnki_id or identifiers.get("filename", "")
    dbcode = identifiers.get("dbcode", "")
    dbname = identifiers.get("dbname", "")
    source_url = item.source_url or item.detail_url
    hit_key = build_hit_key(
        SearchHit(
            title=item.title,
            authors=[item.first_author] if item.first_author else [],
            source="cnki",
            source_url=source_url,
            cnki_id=cnki_id,
            dbcode=dbcode,
            dbname=dbname,
        )
    )
    return {
        "hit_key": hit_key,
        "title": item.title,
        "authors": [item.first_author] if item.first_author else [],
        "source": "cnki",
        "source_url": source_url,
        "local_file": entry.artifact_path,
        "download_format": entry.format,
        "result_type": entry.format and f"downloaded_{entry.format}" or "downloaded_artifact",
        "cnki_id": cnki_id,
        "dbcode": dbcode,
        "dbname": dbname,
    }


class CNKIClient:
    """CNKI download client.

    Local materialization never uses the network. Live browser download is a
    tightly gated visible-browser smoke path and requires explicit confirmation.
    """

    def __init__(self, config: Config | None = None):
        self.config = config or Config.load()

    def _open_browser_for_download(
        self,
        detail_url: str,
        prefer: str = "pdf",
        *,
        confirm_live_access: bool = False,
        mode: str = "managed",
        debug_port: int = 9222,
        download_dir: str | Path | None = None,
        timeout: int = CNKI_DOWNLOAD_TIMEOUT_SECONDS,
        driver_factory=None,
    ) -> DownloadedArtifact | None:
        if not confirm_live_access:
            raise RuntimeError("confirmation_required: CNKI live browser download requires explicit confirmation.")
        if not detail_url:
            raise RuntimeError("missing_target: CNKI detail_url is required for live download.")
        if not is_cnki_url(detail_url):
            raise RuntimeError("invalid_url: only CNKI detail URLs are allowed.")

        mode = (mode or "managed").strip().lower()
        if mode not in {"managed", "attach"}:
            raise RuntimeError("invalid_mode: mode must be managed or attach.")

        target_download_dir = Path(download_dir or self.config.output_dir)
        target_download_dir.mkdir(parents=True, exist_ok=True)
        before = snapshot_cnki_download_dir(target_download_dir)

        driver = _launch_cnki_visible_driver(
            self.config,
            mode=mode,
            debug_port=debug_port,
            driver_factory=driver_factory,
            download_dir=target_download_dir,
        )
        try:
            _set_cnki_browser_download_dir(driver, target_download_dir)
            current_url = getattr(driver, "current_url", "")
            should_reuse_current = mode == "attach" and current_url and current_url.split("#", 1)[0] == detail_url.split("#", 1)[0]
            if not should_reuse_current:
                driver.get(detail_url)
            current_url = getattr(driver, "current_url", detail_url)
            html = getattr(driver, "page_source", "") or ""
            state = detect_cnki_page_state(html, current_url)
            if state in {"manual_login_required", "captcha_required"}:
                raise RuntimeError(f"{state}: 用户需要在可见浏览器内手动完成登录/验证码。")
            if state != "detail_page":
                raise RuntimeError(f"{state or 'unknown'}: 未识别为 CNKI 详情页，未执行下载。")
            detail_paper = parse_cnki_detail(html, url=current_url)

            download_url, expected_format = find_cnki_download_url(html, base_url=current_url, prefer=prefer)
            if not download_url:
                raise RuntimeError("download_link_not_found: 详情页未找到可用下载链接。")
            if not is_cnki_url(download_url):
                raise RuntimeError("invalid_download_url: 下载链接不是允许的 CNKI 域名。")

            clicked = _click_cnki_download_button(driver, expected_format, download_url=download_url)
            if not clicked:
                driver.get(download_url)
            resumed_after_captcha = False
            captcha_waited = False
            if _cnki_driver_is_captcha_or_verify(driver):
                captcha_waited = True
                downloaded = wait_for_cnki_download_after_manual_captcha(
                    driver,
                    target_download_dir,
                    timeout=timeout,
                    extensions={expected_format} if expected_format else CNKI_DOWNLOAD_EXTENSIONS,
                    before=before,
                )
                resumed_after_captcha = downloaded is not None
            else:
                downloaded = wait_for_cnki_download(
                    target_download_dir,
                    timeout=timeout,
                    extensions={expected_format} if expected_format else CNKI_DOWNLOAD_EXTENSIONS,
                    before=before,
                )
                if downloaded is None and _cnki_driver_is_captcha_or_verify(driver):
                    captcha_waited = True
                    downloaded = wait_for_cnki_download_after_manual_captcha(
                        driver,
                        target_download_dir,
                        timeout=timeout,
                        extensions={expected_format} if expected_format else CNKI_DOWNLOAD_EXTENSIONS,
                        before=before,
                    )
                    resumed_after_captcha = downloaded is not None
            if downloaded is None:
                downloaded = _materialize_inline_browser_pdf(
                    driver,
                    source_url=download_url,
                    download_dir=target_download_dir,
                )
            if downloaded is None:
                if captcha_waited:
                    raise RuntimeError("captcha_timeout: 用户未在限定时间内完成 CNKI 验证码，或验证码完成后未发现下载文件。")
                raise RuntimeError("download_timeout: 未在限定时间内发现完成的 CNKI 下载文件。")
            if not _cnki_file_is_new_or_changed(downloaded.path, before):
                raise RuntimeError("download_not_new: 未发现本次新增的 CNKI 下载文件。")
            downloaded.source_url = download_url
            downloaded.metadata = detail_paper
            if resumed_after_captcha:
                downloaded.note = _append_note(downloaded.note, "resumed_after_captcha: 用户在可见浏览器中完成验证码后继续下载。")
            return downloaded
        finally:
            quit_fn = getattr(driver, "quit", None)
            if callable(quit_fn):
                quit_fn()

    def materialize_downloaded_file(
        self,
        paper: Paper,
        file_path: str | Path,
        *,
        source_url: str = "",
        filename_policy: str = "",
        filename_template: str = "",
    ) -> Artifact:
        path = Path(file_path)
        downloaded = DownloadedArtifact(
            content=path.read_bytes(),
            path=path,
            format=path.suffix.lower().lstrip("."),
            source_url=source_url,
        )
        return save_cnki_downloaded_artifact(
            paper,
            downloaded,
            config=self.config,
            filename_policy=filename_policy,
            filename_template=filename_template,
        )

    def download_cnki_artifact(
        self,
        paper: Paper,
        detail_url: str,
        *,
        prefer: str = "pdf",
        filename_policy: str = "",
        filename_template: str = "",
        confirm_live_access: bool = False,
        mode: str = "managed",
        debug_port: int = 9222,
        download_dir: str | Path | None = None,
        timeout: int = CNKI_DOWNLOAD_TIMEOUT_SECONDS,
        driver_factory=None,
    ) -> Artifact | None:
        downloaded = self._open_browser_for_download(
            detail_url,
            prefer=prefer,
            confirm_live_access=confirm_live_access,
            mode=mode,
            debug_port=debug_port,
            download_dir=download_dir,
            timeout=timeout,
            driver_factory=driver_factory,
        )
        if downloaded is None:
            return None
        if not downloaded.source_url:
            downloaded.source_url = detail_url
        if downloaded.metadata is not None:
            metadata = downloaded.metadata
            if not paper.title:
                paper.title = metadata.title
            if not paper.authors:
                paper.authors = metadata.authors
            if not paper.abstract:
                paper.abstract = metadata.abstract
            if not paper.journal:
                paper.journal = metadata.journal
            if not paper.year:
                paper.year = metadata.year
            if not getattr(paper, "cnki_id", ""):
                setattr(paper, "cnki_id", getattr(metadata, "cnki_id", ""))
        return save_cnki_downloaded_artifact(
            paper,
            downloaded,
            config=self.config,
            filename_policy=filename_policy,
            filename_template=filename_template,
        )

    def download_cnki_batch(
        self,
        items: list[CNKIBatchItem],
        *,
        prefer: str = "pdf",
        filename_policy: str = "",
        filename_template: str = "",
        confirm_live_access: bool = False,
        mode: str = "managed",
        debug_port: int = 9222,
        download_dir: str | Path | None = None,
        timeout: int = CNKI_DOWNLOAD_TIMEOUT_SECONDS,
        state_file: str | Path | None = None,
        resume: bool = False,
        min_interval_seconds: float = CNKI_MIN_INTERVAL_SECONDS,
        cooldown_every: int = CNKI_MAX_DOWNLOADS_PER_RUN,
        cooldown_seconds: float = CNKI_MIN_INTERVAL_SECONDS * 3,
        max_consecutive_failures: int = 1,
        root_session_id: str = "",
        source_session_id: str = "",
        derived_session_id: str = "",
        original_query: str = "",
        display_query: str = "",
        recovered_label: str = "",
        actual_queries: list[dict] | None = None,
        sleeper=time.sleep,
        driver_factory=None,
    ) -> CNKIBatchResult:
        """Download CNKI artifacts one by one with conservative pacing.

        This method does not bypass login, captcha, DRM, paywalls, or CNKI
        download limits. It only serializes single-download calls, persists a
        state file, and stops when repeated failures suggest manual intervention.
        """

        if not confirm_live_access:
            raise RuntimeError("confirmation_required: CNKI batch live download requires explicit confirmation.")

        state_path = Path(state_file) if state_file else _default_cnki_batch_state_path(self.config.cache_dir)
        if resume and state_path.exists():
            entries = _load_cnki_batch_state(state_path)
        else:
            entries = [CNKIBatchEntry(item=item) for item in items]
        if not entries:
            _write_cnki_batch_state(state_path, entries, status="completed")
            return CNKIBatchResult(status="completed", state_path=state_path)

        consecutive_failures = 0
        completed_this_run = 0
        stopped_reason = ""

        _write_cnki_batch_state(state_path, entries, status="running")

        for index, entry in enumerate(entries):
            if resume and entry.status in {"succeeded", "failed", "skipped"}:
                continue
            if entry.status == "succeeded":
                continue

            if completed_this_run > 0:
                if cooldown_every > 0 and completed_this_run % int(cooldown_every) == 0:
                    cooldown = float(cooldown_seconds or 0)
                    if cooldown > 0:
                        sleeper(cooldown)
                else:
                    wait_seconds = float(min_interval_seconds or 0)
                    if wait_seconds > 0:
                        sleeper(wait_seconds)

            paper = Paper(
                title=entry.item.title,
                authors=[entry.item.first_author] if entry.item.first_author else [],
                source="cnki",
                url=entry.item.detail_url or entry.item.source_url,
            )
            setattr(paper, "cnki_id", entry.item.cnki_id)
            entry.status = "running"
            entry.error = ""
            entry.started_at = _utc_now_iso()
            entry.attempts += 1
            _write_cnki_batch_state(state_path, entries, status="running")

            try:
                artifact = self.download_cnki_artifact(
                    paper,
                    entry.item.detail_url,
                    prefer=prefer,
                    filename_policy=filename_policy,
                    filename_template=filename_template,
                    confirm_live_access=confirm_live_access,
                    mode=mode,
                    debug_port=debug_port,
                    download_dir=download_dir,
                    timeout=timeout,
                    driver_factory=driver_factory,
                )
                if artifact is None:
                    raise RuntimeError("download_failed: no artifact returned.")
                entry.status = "succeeded"
                entry.artifact_path = artifact.path
                entry.format = artifact.format
                entry.note = artifact.note
                entry.finished_at = _utc_now_iso()
                consecutive_failures = 0
                completed_this_run += 1
            except Exception as e:
                entry.status = "failed"
                entry.error = str(e)
                entry.finished_at = _utc_now_iso()
                consecutive_failures += 1
                completed_this_run += 1
                if max_consecutive_failures > 0 and consecutive_failures >= max_consecutive_failures:
                    stopped_reason = f"max_consecutive_failures:{max_consecutive_failures}"
                    _write_cnki_batch_state(state_path, entries, status="stopped", stopped_reason=stopped_reason)
                    break
            finally:
                if not stopped_reason:
                    _write_cnki_batch_state(state_path, entries, status="running")

        final_status = _cnki_batch_status(entries, stopped_reason=stopped_reason)
        _write_cnki_batch_state(state_path, entries, status=final_status, stopped_reason=stopped_reason)
        sidecar_path = None
        succeeded_entries = [entry for entry in entries if entry.status == "succeeded" and entry.artifact_path]
        if succeeded_entries:
            normalized_display_query = (display_query or "").strip()
            normalized_recovered_label = (recovered_label or "").strip()
            if not normalized_display_query and not normalized_recovered_label:
                normalized_recovered_label = CNKI_DEFAULT_RECOVERED_LABEL
            actual_query_groups = [dict(group) for group in (actual_queries or [])]
            missing_fields = []
            if not root_session_id:
                missing_fields.append("root_session_id")
            if not source_session_id:
                missing_fields.append("source_session_id")
            if not derived_session_id:
                missing_fields.append("derived_session_id")
            if not original_query:
                missing_fields.append("original_query")
            if not actual_query_groups:
                missing_fields.append("actual_queries")
            recovery_capability = "standard" if not missing_fields else "degraded"
            sidecar = DownloadWorkflowSidecar(
                root_session_id=root_session_id,
                source_session_id=source_session_id,
                derived_session_id=derived_session_id,
                original_query=original_query,
                display_query=normalized_display_query,
                recovered_label=normalized_recovered_label,
                actual_queries=actual_query_groups,
                items=[_sidecar_item_from_batch_entry(entry) for entry in succeeded_entries],
                report_recovery_capability=recovery_capability,
                missing_fields=missing_fields,
            )
            sidecar_path = write_download_workflow_sidecar(sidecar, self.config)
        return CNKIBatchResult(
            status=final_status,
            state_path=state_path,
            sidecar_path=sidecar_path,
            entries=entries,
            succeeded=sum(1 for entry in entries if entry.status == "succeeded"),
            failed=sum(1 for entry in entries if entry.status == "failed"),
            skipped=sum(1 for entry in entries if entry.status == "skipped"),
            pending=sum(1 for entry in entries if entry.status == "pending"),
            stopped_reason=stopped_reason,
        )


def _set_cnki_browser_download_dir(driver, download_dir: Path) -> None:
    """Best-effort Chrome download directory setup for managed and attach modes."""

    command = getattr(driver, "execute_cdp_cmd", None)
    if not callable(command):
        return
    params = {"behavior": "allow", "downloadPath": str(download_dir.resolve())}
    for method in ("Browser.setDownloadBehavior", "Page.setDownloadBehavior"):
        try:
            command(method, params)
            return
        except Exception:
            continue


def _materialize_inline_browser_pdf(driver, *, source_url: str, download_dir: Path) -> DownloadedArtifact | None:
    """Read a PDF that Chrome opened inline instead of saving as a download.

    Some CNKI PDF links render directly in Chrome's PDF viewer even after the
    download directory is configured. This helper only reads the already-loaded
    browser resource through CDP; it does not guess hidden endpoints or bypass
    login/captcha checks.
    """

    command = getattr(driver, "execute_cdp_cmd", None)
    if not callable(command):
        return None
    current_url = getattr(driver, "current_url", "") or source_url
    try:
        tree = command("Page.getResourceTree", {})
    except Exception:
        return None

    frame_tree = tree.get("frameTree", {}) if isinstance(tree, dict) else {}
    frame = frame_tree.get("frame", {}) if isinstance(frame_tree, dict) else {}
    frame_id = frame.get("id")
    frame_url = frame.get("url") or current_url
    mime_type = (frame.get("mimeType") or "").lower()
    if not frame_id:
        return None
    if "pdf" not in mime_type and not (frame_url or "").lower().split("?", 1)[0].endswith(".pdf"):
        return None

    try:
        resource = command("Page.getResourceContent", {"frameId": frame_id, "url": frame_url})
    except Exception:
        return None
    content = resource.get("content", "") if isinstance(resource, dict) else ""
    if not content:
        return None
    if resource.get("base64Encoded"):
        try:
            data = base64.b64decode(content)
        except Exception:
            return None
    else:
        data = content.encode("latin1", errors="ignore")
    if not data.startswith(b"%PDF"):
        return None

    name = Path(urlparse(frame_url or source_url).path).name or "cnki-inline.pdf"
    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"
    return DownloadedArtifact(
        content=data,
        path=download_dir / name,
        format="pdf",
        source_url=frame_url or source_url,
    )


def _click_cnki_download_button(driver, expected_format: str, *, download_url: str = "") -> bool:
    """Click the visible CNKI download button to preserve page-origin checks."""

    fmt = (expected_format or "").lower().lstrip(".")
    selectors: list[tuple[str, str]] = []
    if download_url:
        selectors.append(("css selector", f'a[href="{download_url}"]'))
    if fmt == "pdf":
        selectors.append(("id", "pdfDown"))
    elif fmt == "caj":
        selectors.append(("id", "cajDown"))
    elif fmt == "cajx":
        selectors.extend([("id", "cajxDown"), ("id", "cajDown")])
    if not selectors:
        return False

    find_elements = getattr(driver, "find_elements", None)
    if not callable(find_elements):
        return False
    try:
        from selenium.webdriver.common.by import By
    except Exception:
        return False
    by_map = {
        "id": By.ID,
        "css selector": By.CSS_SELECTOR,
    }
    for selector_type, selector_value in selectors:
        try:
            elements = find_elements(by_map.get(selector_type, selector_type), selector_value)
        except TypeError:
            elements = find_elements(selector_type, selector_value)
        except Exception:
            continue
        for element in elements or []:
            if not _cnki_element_matches_download(element, fmt, download_url):
                continue
            _prepare_cnki_click(driver, element)
            click = getattr(element, "click", None)
            if callable(click):
                try:
                    click()
                    return True
                except Exception:
                    pass
            if _script_click_cnki_element(driver, element):
                return True
    return False


def _cnki_element_matches_download(element, expected_format: str, download_url: str) -> bool:
    if download_url:
        get_attribute = getattr(element, "get_attribute", None)
        href = ""
        if callable(get_attribute):
            try:
                href = get_attribute("href") or ""
            except Exception:
                href = ""
        if href and href != download_url:
            return False
    is_displayed = getattr(element, "is_displayed", None)
    if callable(is_displayed):
        try:
            if not is_displayed():
                return False
        except Exception:
            pass
    text = _clean_text(getattr(element, "text", "") or "").lower()
    fmt = (expected_format or "").lower().lstrip(".")
    if fmt == "pdf" and text and "pdf" not in text:
        return False
    if fmt in {"caj", "cajx"} and text and "caj" not in text:
        return False
    return True


def _prepare_cnki_click(driver, element) -> None:
    execute_script = getattr(driver, "execute_script", None)
    if not callable(execute_script):
        return
    try:
        execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", element)
    except Exception:
        return


def _script_click_cnki_element(driver, element) -> bool:
    execute_script = getattr(driver, "execute_script", None)
    if not callable(execute_script):
        return False
    try:
        execute_script("arguments[0].click();", element)
        return True
    except Exception:
        return False
