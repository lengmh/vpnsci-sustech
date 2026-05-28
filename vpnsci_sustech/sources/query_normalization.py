"""Lightweight query normalization for standard search.

This module intentionally uses a small, centralized, testable term table. It
must not become scattered keyword-if logic and must not trigger professional
research mode.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


MAX_QUERY_VARIANTS = 3


@dataclass(frozen=True)
class QueryVariant:
    query: str
    variant_type: str


@dataclass(frozen=True)
class QueryTerm:
    terms: tuple[str, ...]
    translated: str
    abbreviation: str = ""
    domain: str = ""


TERM_TABLE: tuple[QueryTerm, ...] = (
    QueryTerm(("钙钛矿",), "perovskite", domain="materials"),
    QueryTerm(("太阳能电池",), "solar cells", abbreviation="photovoltaics", domain="energy"),
    QueryTerm(("有机光伏", "OPV", "opv"), "organic photovoltaics", abbreviation="organic solar cells", domain="energy"),
    QueryTerm(("稳定性",), "stability"),
    QueryTerm(("大语言模型", "LLM", "llm"), "large language models", abbreviation="LLM", domain="ai"),
    QueryTerm(("检索增强生成", "RAG", "rag"), "retrieval augmented generation", abbreviation="RAG", domain="ai"),
    QueryTerm(("图神经网络", "GNN", "gnn"), "graph neural networks", abbreviation="GNN", domain="ai"),
    QueryTerm(("异常检测",), "anomaly detection", domain="ai"),
    QueryTerm(("非接触", "无接触", "非接触式"), "non-contact"),
    QueryTerm(("体温测量", "体温监测", "体温检测"), "body temperature measurement", abbreviation="body temperature thermometry", domain="medical"),
    QueryTerm(("红外线测量", "红外测量", "红外体温", "红外线"), "infrared measurement", abbreviation="infrared thermography", domain="medical"),
)


def _contains(query: str, term: str) -> bool:
    if re.search(r"[\u4e00-\u9fff]", term):
        return term in query
    return re.search(rf"\b{re.escape(term)}\b", query, flags=re.I) is not None


def _append_unique(parts: list[str], value: str) -> None:
    if value and value not in parts:
        parts.append(value)


def _normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _first_match_position(query: str, entry: QueryTerm) -> int | None:
    positions: list[int] = []
    for term in entry.terms:
        if re.search(r"[\u4e00-\u9fff]", term):
            pos = query.find(term)
            if pos >= 0:
                positions.append(pos)
        else:
            match = re.search(rf"\b{re.escape(term)}\b", query, flags=re.I)
            if match:
                positions.append(match.start())
    return min(positions) if positions else None


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
    """Build at most three query variants and keep original first."""

    original = _normalize_spaces(query)
    if not original:
        return []

    translated_parts: list[str] = []
    abbreviation_parts: list[str] = []
    matched_entries: list[tuple[int, QueryTerm]] = []
    for entry in TERM_TABLE:
        position = _first_match_position(original, entry)
        if position is not None and any(_contains(original, term) for term in entry.terms):
            matched_entries.append((position, entry))

    for _, entry in sorted(matched_entries, key=lambda item: item[0]):
        _append_unique(translated_parts, entry.translated)
        _append_unique(abbreviation_parts, entry.abbreviation or entry.translated)

    variants = [QueryVariant(original, "original")]
    if translated_parts:
        variants.append(QueryVariant(_normalize_spaces(" ".join(translated_parts)), "translated_keywords"))
    if abbreviation_parts and abbreviation_parts != translated_parts:
        variants.append(QueryVariant(_normalize_spaces(" ".join(abbreviation_parts)), "abbreviation_expanded"))

    return _dedupe_variants(variants)
