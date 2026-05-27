"""Unified search result model and merge helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
import re


@dataclass
class SearchError:
    """A classified search-source error."""

    source: str
    code: str
    message: str


@dataclass
class SearchHit:
    """Unified paper metadata returned by search backends."""

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
    openalex_id: str = ""
    s2_paper_id: str = ""
    pmid: str = ""
    pmcid: str = ""
    source: str = ""
    backend: str = ""
    query_variant: str = ""
    query_variant_type: str = ""
    sources: list[str] = field(default_factory=list)
    query_variants: list[str] = field(default_factory=list)


def normalize_doi(value: str) -> str:
    """Normalize DOI while preserving the DOI payload."""

    text = (value or "").strip()
    text = re.sub(r"^https?://(dx\.)?doi\.org/", "", text, flags=re.I)
    text = re.sub(r"^doi:\s*", "", text, flags=re.I)
    return text.strip().lower()


def normalize_arxiv_id(value: str) -> str:
    """Normalize arXiv id from common forms."""

    text = (value or "").strip()
    text = re.sub(r"^arxiv:\s*", "", text, flags=re.I)
    text = re.sub(r"^https?://arxiv\.org/(abs|pdf)/", "", text, flags=re.I)
    return text.removesuffix(".pdf").strip().lower()


def normalize_title(value: str) -> str:
    """Normalize title for conservative title/year fallback matching."""

    text = (value or "").lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def canonical_key(hit: SearchHit) -> str:
    """Return a conservative merge key.

    DOI and arXiv ids are preferred. Title/year is a last resort and is only
    used when stronger identifiers are missing.
    """

    doi = normalize_doi(hit.doi)
    if doi:
        return f"doi:{doi}"
    arxiv_id = normalize_arxiv_id(hit.arxiv_id)
    if arxiv_id:
        return f"arxiv:{arxiv_id}"
    if hit.openalex_id:
        return f"openalex:{hit.openalex_id.strip()}"
    if hit.s2_paper_id:
        return f"s2:{hit.s2_paper_id.strip()}"
    title = normalize_title(hit.title)
    if title:
        return f"title:{title}:{hit.year or ''}"
    if hit.url:
        return f"url:{hit.url.strip().lower()}"
    return f"empty:{id(hit)}"


def _prefer_longer(current: str, incoming: str) -> str:
    current = current or ""
    incoming = incoming or ""
    return incoming if len(incoming) > len(current) else current


def _append_unique(values: list[str], incoming: list[str]) -> list[str]:
    merged: list[str] = []
    for value in [*values, *incoming]:
        if value and value not in merged:
            merged.append(value)
    return merged


def _hit_source(hit: SearchHit) -> str:
    return hit.source or hit.backend


def _variant_marker(hit: SearchHit) -> str:
    if not hit.query_variant:
        return ""
    return f"{hit.query_variant_type or 'unknown'}:{hit.query_variant}"


def merge_hit(base: SearchHit, incoming: SearchHit) -> SearchHit:
    """Merge ``incoming`` metadata into ``base`` in place and return ``base``."""

    base.title = _prefer_longer(base.title, incoming.title)
    base.doi = base.doi or incoming.doi
    base.url = base.url or incoming.url
    base.pdf_url = base.pdf_url or incoming.pdf_url
    base.journal = base.journal or incoming.journal
    base.year = base.year or incoming.year
    base.authors = _append_unique(base.authors, incoming.authors)
    base.citation_count = max(base.citation_count or 0, incoming.citation_count or 0)
    base.abstract = _prefer_longer(base.abstract, incoming.abstract)
    base.arxiv_id = base.arxiv_id or incoming.arxiv_id
    base.openalex_id = base.openalex_id or incoming.openalex_id
    base.s2_paper_id = base.s2_paper_id or incoming.s2_paper_id
    base.pmid = base.pmid or incoming.pmid
    base.pmcid = base.pmcid or incoming.pmcid

    source_values = [*base.sources]
    if _hit_source(base):
        source_values.append(_hit_source(base))
    source_values.extend(incoming.sources)
    if _hit_source(incoming):
        source_values.append(_hit_source(incoming))
    base.sources = _append_unique([], source_values)

    variant_values = [*base.query_variants]
    if _variant_marker(base):
        variant_values.append(_variant_marker(base))
    variant_values.extend(incoming.query_variants)
    if _variant_marker(incoming):
        variant_values.append(_variant_marker(incoming))
    base.query_variants = _append_unique([], variant_values)
    return base


def merge_search_hits(hits: list[SearchHit], *, limit: int | None = None) -> list[SearchHit]:
    """Merge hits by conservative canonical key while preserving input order."""

    by_key: dict[str, SearchHit] = {}
    order: list[str] = []
    for hit in hits:
        key = canonical_key(hit)
        if key not in by_key:
            by_key[key] = hit
            order.append(key)
        else:
            merge_hit(by_key[key], hit)
    merged = [by_key[key] for key in order]
    return merged[:limit] if limit is not None else merged
