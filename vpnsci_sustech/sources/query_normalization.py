"""Query variant normalization for standard search.

This module intentionally keeps runtime behavior query-agnostic. Reviewed
concept aliases belong in the dedicated theme concept alias pipeline, not in a
hidden query expansion table.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


MAX_QUERY_VARIANTS = 3


@dataclass(frozen=True)
class QueryVariant:
    query: str
    variant_type: str


def _normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _dedupe_variants(variants: list[QueryVariant]) -> list[QueryVariant]:
    result: list[QueryVariant] = []
    seen: set[str] = set()
    for variant in variants:
        key = variant.query.lower()
        if variant.query and key not in seen:
            seen.add(key)
            result.append(variant)
    return result[:MAX_QUERY_VARIANTS]


def build_query_variants(query: str) -> list[QueryVariant]:
    """Build query variants and keep original first.

    Runtime no longer performs hidden domain translation/abbreviation expansion.
    Cross-language concept handling is owned by the explicit, reviewed concept
    alias pipeline.
    """

    original = _normalize_spaces(query)
    if not original:
        return []

    return _dedupe_variants([QueryVariant(original, "original")])
