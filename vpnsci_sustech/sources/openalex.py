"""OpenAlex metadata search adapter."""

from __future__ import annotations

import re
import os
from urllib.parse import urlparse

import requests

from .search_models import SearchHit, normalize_doi


OPENALEX_WORKS_URL = "https://api.openalex.org/works"
OPENALEX_SELECT = ",".join(
    [
        "id",
        "doi",
        "display_name",
        "title",
        "publication_year",
        "cited_by_count",
        "abstract_inverted_index",
        "authorships",
        "primary_location",
        "open_access",
        "ids",
        "locations",
    ]
)


class OpenAlexError(RuntimeError):
    """Base OpenAlex error."""


class OpenAlexRateLimitError(OpenAlexError):
    """OpenAlex returned 429 or exhausted allowance."""


class OpenAlexRequestError(OpenAlexError):
    """OpenAlex request failed for non-rate-limit reasons."""


def get_api_key(config_key: str = "") -> str:
    """Get OpenAlex API key from config or environment."""

    return config_key or os.environ.get("OPENALEX_API_KEY", "")


def abstract_from_inverted_index(index: dict | None) -> str:
    """Reconstruct OpenAlex abstract text from an inverted index."""

    if not index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, offsets in index.items():
        for offset in offsets or []:
            positions.append((int(offset), word))
    return " ".join(word for _, word in sorted(positions))


def _strip_external_id_url(value: str) -> str:
    text = value or ""
    if "pubmed.ncbi.nlm.nih.gov" in text:
        return urlparse(text).path.strip("/")
    return text


def _year_filter(year_range: str | None) -> str:
    if not year_range:
        return ""
    text = year_range.strip()
    if re.fullmatch(r"\d{4}", text):
        return f"publication_year:{text}"
    if re.fullmatch(r"\d{4}-\d{4}", text):
        start, end = text.split("-", 1)
        return f"from_publication_date:{start}-01-01,to_publication_date:{end}-12-31"
    if re.fullmatch(r"\d{4}-", text):
        start = text[:4]
        return f"from_publication_date:{start}-01-01"
    return ""


def _best_location(work: dict) -> dict:
    primary = work.get("primary_location") or {}
    if primary:
        return primary
    for location in work.get("locations") or []:
        if location:
            return location
    return {}


def work_to_search_hit(
    work: dict,
    *,
    query_variant: str = "",
    query_variant_type: str = "",
) -> SearchHit:
    """Convert one OpenAlex work into the unified search model."""

    location = _best_location(work)
    source = location.get("source") or {}
    ids = work.get("ids") or {}
    doi = normalize_doi(work.get("doi") or ids.get("doi") or "")
    return SearchHit(
        title=work.get("display_name") or work.get("title") or "",
        doi=doi,
        url=location.get("landing_page_url") or ids.get("doi") or work.get("id") or "",
        pdf_url=location.get("pdf_url") or "",
        journal=source.get("display_name") or "",
        year=work.get("publication_year"),
        authors=[
            author.get("author", {}).get("display_name", "")
            for author in work.get("authorships") or []
            if author.get("author", {}).get("display_name")
        ],
        citation_count=work.get("cited_by_count") or 0,
        abstract=abstract_from_inverted_index(work.get("abstract_inverted_index")),
        openalex_id=work.get("id") or "",
        pmid=_strip_external_id_url(ids.get("pmid") or ""),
        pmcid=ids.get("pmcid") or "",
        source="openalex",
        backend="openalex",
        query_variant=query_variant,
        query_variant_type=query_variant_type,
        sources=["openalex"],
        query_variants=[f"{query_variant_type}:{query_variant}"] if query_variant else [],
    )


def search(
    query: str,
    limit: int = 10,
    year_range: str | None = None,
    api_key: str = "",
    timeout: int = 20,
) -> list[SearchHit]:
    """Search OpenAlex works and return unified hits."""

    params: dict[str, str | int] = {
        "search": query,
        "per_page": max(1, min(limit, 100)),
        "select": OPENALEX_SELECT,
    }
    filter_value = _year_filter(year_range)
    if filter_value:
        params["filter"] = filter_value
    resolved_key = get_api_key(api_key)
    if resolved_key:
        params["api_key"] = resolved_key

    try:
        response = requests.get(OPENALEX_WORKS_URL, params=params, timeout=timeout)
    except requests.RequestException as e:
        raise OpenAlexRequestError(str(e)) from e

    if response.status_code == 429:
        raise OpenAlexRateLimitError("OpenAlex returned HTTP 429")
    if response.status_code >= 400:
        raise OpenAlexRequestError(f"OpenAlex returned HTTP {response.status_code}: {response.text[:200]}")

    try:
        payload = response.json()
    except ValueError as e:
        raise OpenAlexRequestError(f"OpenAlex returned invalid JSON: {e}") from e

    return [
        work_to_search_hit(item, query_variant=query, query_variant_type="")
        for item in payload.get("results", [])
    ]
