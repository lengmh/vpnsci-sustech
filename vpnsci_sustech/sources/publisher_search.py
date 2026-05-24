"""Publisher-native search helpers for Phase 2."""

from dataclasses import dataclass, field
from pathlib import Path
import re
import time
from urllib.parse import urlencode, urljoin, quote_plus

from bs4 import BeautifulSoup
import requests

from ..browser_session import ChromeDebugSessionManager
from ..config import Config
from ..http_clients import SiteRateLimiter, create_http_client
from ..site_policy import PHASE2_MIN_INTERVAL_SECONDS


@dataclass
class SearchHit:
    title: str = ""
    doi: str = ""
    url: str = ""
    pdf_url: str = ""
    journal: str = ""
    year: int | None = None
    authors: list[str] = field(default_factory=list)
    citation_count: int = 0
    abstract: str = ""
    arxiv_id: str = ""


class PublisherSearchError(RuntimeError):
    """Base error for publisher-native search failures."""


class PublisherSearchBlockedError(PublisherSearchError):
    """Raised when a site returns a challenge/blocked page."""


_SITE_LIMITER = SiteRateLimiter(min_interval_seconds=PHASE2_MIN_INTERVAL_SECONDS)


def looks_like_access_challenge(html: str) -> bool:
    lowered = (html or "").lower()
    strong_signals = [
        "just a moment",
        "verify you are human",
        "cf-browser-verification",
        "access denied",
        "complete this security check",
        "security verification",
        "are you a robot",
    ]
    if any(signal in lowered for signal in strong_signals):
        return True

    # Some publisher pages include Cloudflare assets or robots meta tags even when
    # the main content is still a normal searchable result page. Only treat those
    # as blocking when result/article signals are absent.
    weak_signals = [
        "challenge-platform",
        "captcha",
        "robot",
    ]
    has_weak_signal = any(signal in lowered for signal in weak_signals)
    if not has_weak_signal:
        return False

    has_normal_result_signal = any(
        signal in lowered
        for signal in [
            "/science/article/pii/",
            "/article/10.",
            "/doi/10.",
            "search | sciencedirect.com",
            "advanced search - wiley online library",
            "advanced search",
            'action="/action/dosearch"',
            "publication[]",
            "view pdf",
            "results-content",
        ]
    )
    return not has_normal_result_signal


def resolve_backend(site: str) -> str:
    key = site.strip().lower()
    aliases = {
        "sciencedirect": "sciencedirect",
        "elsevier": "sciencedirect",
        "springer": "springerlink",
        "springerlink": "springerlink",
        "nature": "springerlink",
        "wiley": "wiley",
    }
    return aliases[key]


def search(query: str, *, backend: str, limit: int = 10) -> list[SearchHit]:
    resolved = resolve_backend(backend)
    if resolved == "sciencedirect":
        return search_sciencedirect(query, limit=limit, allow_browser_fallback=True)
    if resolved == "springerlink":
        return search_springer(query, limit=limit)
    if resolved == "wiley":
        return search_wiley(query, limit=limit)
    return []


def search_sciencedirect(query: str, limit: int = 10, allow_browser_fallback: bool = False) -> list[SearchHit]:
    client = create_http_client(prefer_impersonation=True)
    params = {"qs": query}
    _SITE_LIMITER.wait("sciencedirect")
    page = client.get(f"https://www.sciencedirect.com/search?{urlencode(params)}", timeout=30, headers={"Cookie": ""})
    if looks_like_access_challenge(page.text):
        if allow_browser_fallback:
            return _search_sciencedirect_via_browser(query, limit=limit)
        raise PublisherSearchBlockedError("ScienceDirect search page returned challenge")
    if page.status_code != 200:
        if allow_browser_fallback:
            return _search_sciencedirect_via_browser(query, limit=limit)
        return []
    token_match = re.search(r'"searchToken":"([^"]+)"', page.text)
    if not token_match:
        if allow_browser_fallback:
            return _search_sciencedirect_via_browser(query, limit=limit)
        return []
    token = token_match.group(1)
    api_params = dict(params)
    api_params["t"] = token
    api_params["hostname"] = "www.sciencedirect.com"
    _SITE_LIMITER.wait("sciencedirect")
    resp = client.get(
        f"https://www.sciencedirect.com/search/api?{urlencode(api_params)}",
        timeout=30,
        headers={
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": f"https://www.sciencedirect.com/search?{urlencode(params)}",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    if hasattr(resp, "text") and looks_like_access_challenge(getattr(resp, "text", "")):
        if allow_browser_fallback:
            return _search_sciencedirect_via_browser(query, limit=limit)
        raise PublisherSearchBlockedError("ScienceDirect search API returned challenge page")
    if resp.status_code != 200:
        if allow_browser_fallback:
            return _search_sciencedirect_via_browser(query, limit=limit)
        return []
    hits = parse_sciencedirect_search_api(resp.json())[:limit]
    if not hits and allow_browser_fallback:
        return _search_sciencedirect_via_browser(query, limit=limit)
    return hits


def _search_sciencedirect_via_browser(query: str, limit: int = 10) -> list[SearchHit]:
    _SITE_LIMITER.wait("sciencedirect")
    mgr = _build_browser_session_manager()
    driver = None
    try:
        driver = mgr.launch_browser(enable_debug=False, extra_args=["--window-size=1400,1000"])
        driver.get(f"https://www.sciencedirect.com/search?qs={quote_plus(query)}")
        dom_hits = []
        for _ in range(15):
            dom_hits = parse_sciencedirect_search_results_dom(driver)
            if dom_hits:
                return dom_hits[:limit]
            time.sleep(1)
        return parse_sciencedirect_search_results_html(driver.page_source)[:limit]
    finally:
        if driver:
            driver.quit()


def search_springer(query: str, limit: int = 10, allow_browser_fallback: bool = False) -> list[SearchHit]:
    client = create_http_client(prefer_impersonation=False)
    _SITE_LIMITER.wait("springerlink")
    resp = client.get(
        f"https://link.springer.com/search?query={query}",
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    if looks_like_access_challenge(resp.text):
        if allow_browser_fallback:
            return _search_springer_via_browser(query, limit=limit)
        return _search_springer_via_crossref(query, limit=limit)
    if resp.status_code != 200:
        return []
    native_hits = parse_springer_search_html(resp.text)[:limit]
    cross_hits = _search_springer_via_crossref(query, limit=limit)
    return _merge_search_hits(native_hits, cross_hits, limit=limit)


def _search_springer_via_browser(query: str, limit: int = 10) -> list[SearchHit]:
    _SITE_LIMITER.wait("springerlink")
    mgr = _build_browser_session_manager()
    driver = None
    try:
        driver = mgr.launch_browser(enable_debug=False, extra_args=["--window-size=1400,1000"])
        driver.get(f"https://link.springer.com/search?query={query}")
        return parse_springer_search_html(driver.page_source)[:limit]
    finally:
        if driver:
            driver.quit()


def _search_springer_via_crossref(query: str, limit: int = 10) -> list[SearchHit]:
    url = f"https://api.crossref.org/works?query.title={quote_plus(query)}&rows={max(limit, 10)}"
    resp = requests.get(
        url,
        timeout=30,
        headers={"User-Agent": "vpnsci-sustech/0.1 (mailto:test@example.com)"},
    )
    resp.raise_for_status()
    items = resp.json().get("message", {}).get("items", [])
    hits = []
    for item in items:
        publisher = (item.get("publisher") or "").lower()
        if "springer" not in publisher:
            continue
        doi = item.get("DOI", "")
        title = " ".join(item.get("title", [])[:1]).strip()
        journal = " ".join(item.get("container-title", [])[:1]).strip()
        if not doi or not title:
            continue
        hits.append(
            SearchHit(
                title=title,
                doi=doi,
                url=f"https://link.springer.com/article/{doi}",
                pdf_url=f"https://link.springer.com/content/pdf/{doi}.pdf",
                journal=journal,
                year=item.get("published-print", {}).get("date-parts", [[None]])[0][0]
                    or item.get("published-online", {}).get("date-parts", [[None]])[0][0],
            )
        )
        if len(hits) >= limit:
            break
    return hits


def _merge_search_hits(primary: list[SearchHit], fallback: list[SearchHit], *, limit: int) -> list[SearchHit]:
    merged = []
    seen = set()
    for seq in (fallback, primary):
        for hit in seq:
            key = (hit.doi or "", hit.url or "", hit.title or "")
            if key in seen:
                continue
            seen.add(key)
            merged.append(hit)
            if len(merged) >= limit:
                return merged
    return merged


def search_wiley(query: str, limit: int = 10, allow_browser_fallback: bool = False) -> list[SearchHit]:
    client = create_http_client(prefer_impersonation=False)
    _SITE_LIMITER.wait("wiley")
    resp = client.get(
        f"https://onlinelibrary.wiley.com/action/doSearch?AllField={query}",
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    if looks_like_access_challenge(resp.text):
        if allow_browser_fallback:
            return _search_wiley_via_browser(query, limit=limit)
        return _search_wiley_via_crossref(query, limit=limit)
    if resp.status_code != 200:
        return []
    return parse_wiley_search_html(resp.text)[:limit]


def _search_wiley_via_browser(query: str, limit: int = 10) -> list[SearchHit]:
    from selenium.webdriver.common.by import By

    _SITE_LIMITER.wait("wiley")
    mgr = _build_browser_session_manager()
    driver = None
    try:
        driver = mgr.launch_browser(enable_debug=False, extra_args=["--window-size=1400,1000"])
        driver.get("https://onlinelibrary.wiley.com/search/advanced?publication=15213773")
        time.sleep(5)
        form = None
        for f in driver.find_elements(By.CSS_SELECTOR, 'form[action*="/action/doSearch"]'):
            try:
                form_id = (f.get_attribute("id") or "").lower()
                form_class = (f.get_attribute("class") or "").lower()
                if form_id == "frmsearch" or "advanced-search" in form_class:
                    form = f
                    break
            except Exception:
                pass
        if form is not None:
            inputs = form.find_elements(By.CSS_SELECTOR, '#text1, input[id="text1"]')
            if inputs:
                try:
                    inputs[0].clear()
                except Exception:
                    pass
                inputs[0].send_keys(query)
                time.sleep(1)
                submits = form.find_elements(By.CSS_SELECTOR, '#advanced-search-btn, button[type="submit"], input[type="submit"]')
                if submits:
                    try:
                        submits[0].click()
                    except Exception:
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", submits[0])
                        except Exception:
                            pass
                        driver.execute_script("arguments[0].click();", submits[0])
                    time.sleep(8)
                    return parse_wiley_search_html(driver.page_source)[:limit]
        driver.get(f"https://onlinelibrary.wiley.com/action/doSearch?AllField={query}")
        return parse_wiley_search_html(driver.page_source)[:limit]
    finally:
        if driver:
            driver.quit()


def _search_wiley_via_crossref(query: str, limit: int = 10) -> list[SearchHit]:
    url = f"https://api.crossref.org/works?query.title={quote_plus(query)}&rows={max(limit, 5)}"
    resp = requests.get(
        url,
        timeout=30,
        headers={"User-Agent": "vpnsci-sustech/0.1 (mailto:test@example.com)"},
    )
    resp.raise_for_status()
    items = resp.json().get("message", {}).get("items", [])
    hits = []
    for item in items:
        if (item.get("publisher") or "").lower() != "wiley":
            continue
        doi = item.get("DOI", "")
        title = " ".join(item.get("title", [])[:1]).strip()
        journal = " ".join(item.get("container-title", [])[:1]).strip()
        if not doi or not title:
            continue
        hits.append(
            SearchHit(
                title=title,
                doi=doi,
                url=f"https://onlinelibrary.wiley.com/doi/{doi}",
                pdf_url=f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}",
                journal=journal,
                year=item.get("published-print", {}).get("date-parts", [[None]])[0][0]
                    or item.get("published-online", {}).get("date-parts", [[None]])[0][0],
            )
        )
        if len(hits) >= limit:
            break
    return hits


def _build_browser_session_manager() -> ChromeDebugSessionManager:
    cfg = Config.load()
    return ChromeDebugSessionManager(
        base_dir=Path(cfg.cache_dir) if getattr(cfg, "cache_dir", "") else Path.home() / ".vpnsci-sustech" / "cache",
        profile_root_name="chrome-profile",
    )


def parse_sciencedirect_search_api(payload: dict) -> list[SearchHit]:
    hits = []
    for item in payload.get("searchResults", []):
        pii = item.get("pii", "")
        url = item.get("link", "") or item.get("slug", "") or (f"/science/article/pii/{pii}" if pii else "")
        doi = item.get("doi", "") or item.get("doiLink", "")
        pub_date = item.get("publicationDate", "") or item.get("sortDate", "") or item.get("publicationDateDisplay", "")
        year = None
        if pub_date:
            year_match = re.search(r"\b(19|20)\d{2}\b", pub_date)
            if year_match:
                year = int(year_match.group(0))
        pdf = item.get("pdf") or {}
        pdf_link = pdf.get("downloadLink") or ""
        pdf_url = urljoin("https://www.sciencedirect.com", pdf_link) if pdf_link else (
            f"https://www.sciencedirect.com/science/article/pii/{pii}/pdfft" if pii else ""
        )
        hits.append(
            SearchHit(
                title=BeautifulSoup(item.get("title", ""), "lxml").get_text(" ", strip=True),
                doi=doi,
                url=urljoin("https://www.sciencedirect.com", url),
                pdf_url=pdf_url,
                journal=item.get("sourceTitle", ""),
                year=year,
                authors=[a.get("name", "") for a in (item.get("authors") or []) if a.get("name")],
            )
        )
    return hits


def parse_sciencedirect_search_results_html(html: str) -> list[SearchHit]:
    soup = BeautifulSoup(html, "lxml")
    hits = []
    seen_urls = set()
    for a in soup.select("a[href*='/science/article/pii/']"):
        href = a.get("href", "")
        if "/pdfft" in href.lower():
            continue
        url = urljoin("https://www.sciencedirect.com", href)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        title = a.get_text(" ", strip=True)
        pii_match = re.search(r"/pii/([A-Z0-9]+)", href, flags=re.I)
        pii = pii_match.group(1) if pii_match else ""
        pdf_url = ""
        if pii:
            # Search pages often expose a more realistic View PDF href with pid query.
            pdf_link = soup.select_one(f"a[href*='/science/article/pii/{pii}/pdfft']")
            if pdf_link and pdf_link.get("href"):
                pdf_url = urljoin("https://www.sciencedirect.com", pdf_link.get("href"))
            else:
                pdf_url = f"https://www.sciencedirect.com/science/article/pii/{pii}/pdfft"
        hits.append(
            SearchHit(
                title=title,
                doi="",
                url=url,
                pdf_url=pdf_url,
                journal="",
                year=None,
            )
        )
    return hits


def parse_sciencedirect_search_results_dom(driver) -> list[SearchHit]:
    hits = []
    seen_urls = set()
    article_links = []
    pdf_links = {}
    for el in driver.find_elements("css selector", "a[href]"):
        href = el.get_attribute("href") or ""
        text = (getattr(el, "text", "") or "").strip()
        lowered = href.lower()
        if "/science/article/pii/" in lowered and "/pdfft" not in lowered:
            article_links.append((el, href, text))
        elif "/science/article/pii/" in lowered and "/pdfft" in lowered:
            pii_match = re.search(r"/pii/([A-Z0-9]+)", href, flags=re.I)
            if pii_match:
                pdf_links[pii_match.group(1)] = href

    for el, href, text in article_links:
        if href in seen_urls:
            continue
        seen_urls.add(href)
        pii_match = re.search(r"/pii/([A-Z0-9]+)", href, flags=re.I)
        pii = pii_match.group(1) if pii_match else ""
        pdf_url = pdf_links.get(pii, f"https://www.sciencedirect.com/science/article/pii/{pii}/pdfft" if pii else "")
        journal = ""
        year = None
        try:
            parent_text = getattr(el, "parent_text", "") or ""
            if not parent_text and hasattr(el, "find_element"):
                try:
                    parent = el.find_element("xpath", "./ancestor::*[self::li or self::article or self::div][1]")
                    parent_text = getattr(parent, "text", "") or ""
                except Exception:
                    parent_text = ""
            year_match = re.search(r"\b(19|20)\d{2}\b", parent_text)
            if year_match:
                year = int(year_match.group(0))
            if parent_text:
                journal_line = parent_text.splitlines()
                for line in journal_line:
                    line = line.strip()
                    if not line or line == text or "view pdf" in line.lower():
                        continue
                    lowered_line = line.lower()
                    if "research article" in lowered_line or "open access" in lowered_line or "full text access" in lowered_line:
                        continue
                    candidate = re.sub(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s*(19|20)\d{2}\b.*$", "", line, flags=re.I)
                    candidate = re.sub(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+(19|20)\d{2}\b.*$", "", candidate, flags=re.I)
                    candidate = re.sub(r"\b(19|20)\d{2}\b.*$", "", candidate).strip(" ,;:-")
                    if candidate:
                        journal = candidate
                        break
        except Exception:
            pass
        hits.append(
            SearchHit(
                title=text,
                doi="",
                url=href,
                pdf_url=pdf_url,
                journal=journal,
                year=year,
            )
        )
    return hits


def parse_springer_search_html(html: str) -> list[SearchHit]:
    soup = BeautifulSoup(html, "lxml")
    hits = []
    for a in soup.select("a[href*='/article/10.']"):
        href = a.get("href", "")
        title = a.get_text(strip=True)
        doi_match = re.search(r"/article/(10\.\d{4,9}/[^\s?#]+)", href)
        if not doi_match:
            continue
        doi = doi_match.group(1)
        parent_text = a.parent.get_text(" ", strip=True) if a.parent else ""
        year_match = re.search(r"\b(19|20)\d{2}\b", parent_text)
        hits.append(
            SearchHit(
                title=title,
                doi=doi,
                url=urljoin("https://link.springer.com", href),
                pdf_url=f"https://link.springer.com/content/pdf/{doi}.pdf",
                journal="",
                year=int(year_match.group(0)) if year_match else None,
            )
        )
    return hits


def parse_wiley_search_html(html: str) -> list[SearchHit]:
    soup = BeautifulSoup(html, "lxml")
    hits = []
    for a in soup.select("a[href*='/doi/10.']"):
        href = a.get("href", "")
        title = a.get_text(strip=True)
        doi_match = re.search(r"/doi/(?:abs/|full/|epdf/|pdf/)?(10\.\d{4,9}/[^\s?#]+)", href)
        if not doi_match:
            continue
        doi = doi_match.group(1).rstrip("/")
        parent_text = a.parent.get_text(" ", strip=True) if a.parent else ""
        year_match = re.search(r"\b(19|20)\d{2}\b", parent_text)
        hits.append(
            SearchHit(
                title=title,
                doi=doi,
                url=urljoin("https://onlinelibrary.wiley.com", href),
                pdf_url=f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}",
                journal="",
                year=int(year_match.group(0)) if year_match else None,
            )
        )
    return hits
