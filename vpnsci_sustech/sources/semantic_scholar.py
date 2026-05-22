"""Paper search via Semantic Scholar API."""

import logging
import os
import time
from dataclasses import dataclass, field

import requests

logger = logging.getLogger(__name__)

S2_API = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "title,authors,year,abstract,externalIds,journal,citationCount,url"
MAX_RETRIES = 3
API_KEY_MIN_INTERVAL_SECONDS = 1.0
_last_api_key_request_at = 0.0


class SemanticScholarError(RuntimeError):
    """Base error for Semantic Scholar failures."""


class SemanticScholarRateLimitError(SemanticScholarError):
    """Raised when Semantic Scholar search is rate limited."""


class SemanticScholarRequestError(SemanticScholarError):
    """Raised when Semantic Scholar request fails for non-rate-limit reasons."""


@dataclass
class SearchResult:
    """A single search result from Semantic Scholar."""

    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    abstract: str = ""
    doi: str = ""
    arxiv_id: str = ""
    journal: str = ""
    citation_count: int = 0
    s2_url: str = ""
    paper_id: str = ""


def get_api_key(config_key: str = "") -> str:
    """Get Semantic Scholar API key from config or environment."""
    return config_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")


def _throttle_api_key_requests():
    """Throttle authenticated requests to 1 request per second."""
    global _last_api_key_request_at
    now = time.monotonic()
    elapsed = now - _last_api_key_request_at
    if elapsed < API_KEY_MIN_INTERVAL_SECONDS:
        wait = API_KEY_MIN_INTERVAL_SECONDS - elapsed
        time.sleep(wait)
        now = time.monotonic()
    _last_api_key_request_at = now


def _build_headers(api_key: str = "") -> dict[str, str]:
    if not api_key:
        return {}
    return {"x-api-key": api_key}


def _request_with_retry(url: str, params: dict, api_key: str = "") -> dict | None:
    """Make a GET request with retry on 429 rate limit."""
    headers = _build_headers(api_key)
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            if api_key:
                _throttle_api_key_requests()
            resp = requests.get(url, params=params, timeout=15, headers=headers)
            if resp.status_code == 404:
                return None
            if resp.status_code == 429:
                wait = 2 ** (attempt + 1)
                logger.warning("Rate limited by Semantic Scholar, retrying in %ds...", wait)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(wait)
                    continue
                raise SemanticScholarRateLimitError("Semantic Scholar returned HTTP 429")
            resp.raise_for_status()
            return resp.json()
        except SemanticScholarRateLimitError:
            raise
        except requests.RequestException as e:
            last_error = e
            logger.error("Semantic Scholar request failed: %s", e)
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)
            else:
                raise SemanticScholarRequestError(str(e)) from e
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)
            else:
                raise SemanticScholarRequestError(str(e)) from e

    if last_error is not None:
        raise SemanticScholarRequestError(str(last_error)) from last_error
    return None


def _parse_results(data: dict) -> list[SearchResult]:
    results = []
    for item in data.get("data", []):
        ext_ids = item.get("externalIds") or {}
        authors_data = item.get("authors") or []
        journal_data = item.get("journal") or {}

        result = SearchResult(
            title=item.get("title", ""),
            authors=[a.get("name", "") for a in authors_data if a.get("name")],
            year=item.get("year"),
            abstract=item.get("abstract") or "",
            doi=ext_ids.get("DOI", ""),
            arxiv_id=ext_ids.get("ArXiv", ""),
            journal=journal_data.get("name", "") if isinstance(journal_data, dict) else str(journal_data),
            citation_count=item.get("citationCount", 0),
            s2_url=item.get("url", ""),
            paper_id=item.get("paperId", ""),
        )
        results.append(result)
    return results


def search(
    query: str,
    limit: int = 10,
    year_range: str | None = None,
    fields_of_study: list[str] | None = None,
    api_key: str = "",
) -> list[SearchResult]:
    """Search for papers on Semantic Scholar.

    Anonymous search is attempted first. If it is rate-limited and an API key
    is available, retry once with the key.
    """
    params = {
        "query": query,
        "limit": min(limit, 100),
        "fields": S2_FIELDS,
    }
    if year_range:
        params["year"] = year_range
    if fields_of_study:
        params["fieldsOfStudy"] = ",".join(fields_of_study)

    try:
        data = _request_with_retry(f"{S2_API}/paper/search", params)
    except SemanticScholarRateLimitError:
        resolved_key = get_api_key(api_key)
        if not resolved_key:
            raise
        data = _request_with_retry(f"{S2_API}/paper/search", params, api_key=resolved_key)

    if data is None:
        return []
    return _parse_results(data)


def get_paper(paper_id: str, api_key: str = "") -> SearchResult | None:
    """Get details for a specific paper by Semantic Scholar ID or DOI."""
    resolved_key = get_api_key(api_key)
    item = _request_with_retry(
        f"{S2_API}/paper/{paper_id}",
        {"fields": S2_FIELDS},
        api_key=resolved_key,
    )
    if item is None:
        return None

    ext_ids = item.get("externalIds") or {}
    authors_data = item.get("authors") or []
    journal_data = item.get("journal") or {}

    return SearchResult(
        title=item.get("title", ""),
        authors=[a.get("name", "") for a in authors_data if a.get("name")],
        year=item.get("year"),
        abstract=item.get("abstract") or "",
        doi=ext_ids.get("DOI", ""),
        arxiv_id=ext_ids.get("ArXiv", ""),
        journal=journal_data.get("name", "") if isinstance(journal_data, dict) else str(journal_data),
        citation_count=item.get("citationCount", 0),
        s2_url=item.get("url", ""),
        paper_id=item.get("paperId", ""),
    )
