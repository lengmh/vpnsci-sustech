"""Default OpenAlex-first standard search orchestration."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from ..config import Config
from . import openalex, semantic_scholar
from .query_normalization import QueryVariant, build_query_variants
from .search_cache import SearchSession, load_cached_hits, new_session_id, save_cached_hits, save_session
from .search_mode import should_show_upgrade_suggestion
from .search_models import SearchError, SearchHit, merge_search_hits


def _cache_dir(config: Config) -> Path:
    return Path(config.cache_dir)


def _source_summary(hits: list[SearchHit]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for hit in hits:
        source_names = hit.sources or [hit.source or hit.backend or "unknown"]
        for source in source_names:
            counts[source] += 1
    return dict(counts)


def _mark_variant(hit: SearchHit, variant: QueryVariant, source: str) -> SearchHit:
    hit.query_variant = hit.query_variant or variant.query
    hit.query_variant_type = hit.query_variant_type or variant.variant_type
    hit.source = hit.source or source
    hit.backend = hit.backend or source
    if source and source not in hit.sources:
        hit.sources.append(source)
    marker = f"{variant.variant_type}:{variant.query}"
    if marker not in hit.query_variants:
        hit.query_variants.append(marker)
    return hit


def _search_openalex_variant(
    variant: QueryVariant,
    *,
    limit: int,
    year_range: str | None,
    config: Config,
) -> tuple[list[SearchHit], list[SearchError]]:
    filters = {"limit": limit, "year_range": year_range or ""}
    cached = load_cached_hits("openalex", variant.query, filters, _cache_dir(config))
    if cached is not None:
        return [_mark_variant(hit, variant, "openalex") for hit in cached], []
    try:
        hits = openalex.search(
            variant.query,
            limit=limit,
            year_range=year_range,
            api_key=config.openalex_api_key,
        )
        marked = [_mark_variant(hit, variant, "openalex") for hit in hits]
        save_cached_hits("openalex", variant.query, filters, marked, _cache_dir(config))
        return marked, []
    except openalex.OpenAlexRateLimitError as e:
        return [], [SearchError(source="openalex", code="rate_limited", message=str(e))]
    except openalex.OpenAlexRequestError as e:
        return [], [SearchError(source="openalex", code="request_failed", message=str(e))]


def _search_s2_variant(
    variant: QueryVariant,
    *,
    limit: int,
    year_range: str | None,
    config: Config,
) -> tuple[list[SearchHit], list[SearchError]]:
    filters = {"limit": limit, "year_range": year_range or ""}
    cached = load_cached_hits("semantic_scholar", variant.query, filters, _cache_dir(config))
    if cached is not None:
        return [_mark_variant(hit, variant, "semantic_scholar") for hit in cached], []
    try:
        results = semantic_scholar.search(
            variant.query,
            limit=limit,
            year_range=year_range,
            api_key=config.semantic_scholar_api_key,
        )
        hits = [
            semantic_scholar.to_search_hit(
                result,
                query_variant=variant.query,
                query_variant_type=variant.variant_type,
            )
            for result in results
        ]
        save_cached_hits("semantic_scholar", variant.query, filters, hits, _cache_dir(config))
        return hits, []
    except semantic_scholar.SemanticScholarRateLimitError as e:
        return [], [SearchError(source="semantic_scholar", code="rate_limited", message=str(e))]
    except semantic_scholar.SemanticScholarRequestError as e:
        return [], [SearchError(source="semantic_scholar", code="request_failed", message=str(e))]


def search(
    query: str,
    limit: int = 10,
    year_range: str | None = None,
    *,
    config: Config | None = None,
    enrich_with_s2: bool = False,
) -> SearchSession:
    """Run standard search and persist a search session."""

    config = config or Config.load()
    variants = build_query_variants(query)
    all_hits: list[SearchHit] = []
    errors: list[SearchError] = []

    for variant in variants:
        hits, source_errors = _search_openalex_variant(
            variant,
            limit=limit,
            year_range=year_range,
            config=config,
        )
        all_hits.extend(hits)
        errors.extend(source_errors)

    should_fallback_to_s2 = len(all_hits) < limit or enrich_with_s2
    if should_fallback_to_s2:
        for variant in variants:
            hits, source_errors = _search_s2_variant(
                variant,
                limit=limit,
                year_range=year_range,
                config=config,
            )
            all_hits.extend(hits)
            errors.extend(source_errors)

    merged = merge_search_hits(all_hits, limit=limit)
    upgrade = should_show_upgrade_suggestion(query, merged, errors, is_standard_search=True)
    session = SearchSession(
        session_id=new_session_id(),
        query=query,
        filters={"year_range": year_range or "", "limit": limit, "query_variants": [v.__dict__ for v in variants]},
        hits=merged,
        source_summary=_source_summary(merged),
        errors=errors,
        upgrade_suggested=upgrade.show,
        decision_reasons=upgrade.reasons,
    )
    save_session(session, _cache_dir(config))
    return session
