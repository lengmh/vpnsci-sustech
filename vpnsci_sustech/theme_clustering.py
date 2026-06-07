"""Shared deterministic theme clustering helpers for report rendering."""

from __future__ import annotations

from collections import Counter, defaultdict
import re
from typing import Any


THEME_STOPWORDS_EN = {
    "about",
    "across",
    "after",
    "algorithm",
    "algorithms",
    "an",
    "and",
    "analysis",
    "analyses",
    "approach",
    "approaches",
    "as",
    "article",
    "articles",
    "assessment",
    "at",
    "by",
    "based",
    "between",
    "case",
    "clinical",
    "comparison",
    "data",
    "dataset",
    "datasets",
    "effect",
    "effects",
    "evaluation",
    "in",
    "into",
    "for",
    "from",
    "finding",
    "findings",
    "framework",
    "frameworks",
    "journal",
    "method",
    "methods",
    "model",
    "models",
    "new",
    "of",
    "on",
    "paper",
    "papers",
    "research",
    "result",
    "results",
    "review",
    "reviews",
    "the",
    "this",
    "those",
    "through",
    "to",
    "study",
    "studies",
    "survey",
    "surveys",
    "system",
    "systems",
    "their",
    "these",
    "via",
    "using",
    "we",
    "with",
}
THEME_STOPWORDS_ZH = {
    "研究",
    "分析",
    "方法",
    "系统",
    "模型",
    "应用",
    "综述",
    "进展",
    "实验",
    "结果",
    "影响",
    "评价",
    "比较",
    "案例",
    "数据",
    "基于",
    "面向",
    "相关",
}
THEME_ACRONYMS = {"ai", "ct", "dna", "mri", "nlp", "pcr", "rna", "svm"}
ENGLISH_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9-]*")
CHINESE_SEGMENT_RE = re.compile(r"[\u4e00-\u9fff]{2,20}")


def display_theme_name(term: str) -> str:
    if any("\u4e00" <= ch <= "\u9fff" for ch in term):
        return term
    words = []
    for token in term.split():
        if token in THEME_ACRONYMS:
            words.append(token.upper())
        else:
            words.append(token.capitalize())
    return " ".join(words)


def build_keyword_topic_themes(
    items: list[dict[str, Any]],
    *,
    paper_id_key: str = "paper_id",
    keyword_field: str = "keywords",
    topics_field: str = "topics",
    min_papers: int = 2,
    max_themes: int = 8,
) -> dict[str, Any]:
    keyword_counts: Counter[str] = Counter()
    keyword_to_papers: dict[str, list[str]] = defaultdict(list)
    for index, item in enumerate(items, 1):
        paper_id = str(item.get(paper_id_key) or item.get("id") or f"paper-{index}")
        kw_sources: list[str] = []
        for kw in (item.get(keyword_field) or []):
            if isinstance(kw, str):
                kw_sources.append(kw.lower().strip())
        for topic in (item.get(topics_field) or []):
            if isinstance(topic, dict):
                name = topic.get("display_name") or topic.get("name")
                if name:
                    kw_sources.append(str(name).lower().strip())
            elif isinstance(topic, str):
                kw_sources.append(topic.lower().strip())
        for kw in set(kw_sources):
            if not kw or len(kw) > 60:
                continue
            keyword_counts[kw] += 1
            keyword_to_papers[kw].append(paper_id)

    top = [(k, c) for k, c in keyword_counts.most_common(20) if c >= min_papers][:max_themes]
    themes = [
        {
            "name": display_theme_name(keyword),
            "value": count,
            "paper_ids": keyword_to_papers[keyword][:20],
        }
        for keyword, count in top
    ]
    return {"themes": themes, "total_papers": len(items)}


def _paper_text(paper: dict[str, Any]) -> str:
    return " ".join(
        str(paper.get(key) or "")
        for key in ("title", "abstract", "venue", "journal")
    ).lower()


def _normalize_english_token(token: str) -> str:
    token = token.lower().strip("-")
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _english_term_candidates(text: str) -> list[str]:
    tokens = []
    for raw in ENGLISH_TOKEN_RE.findall(text.lower()):
        token = _normalize_english_token(raw)
        if token in THEME_STOPWORDS_EN:
            continue
        if len(token) < 3 and token not in THEME_ACRONYMS:
            continue
        tokens.append(token)

    candidates = list(tokens)
    for width in (2,):
        for index in range(len(tokens) - width + 1):
            candidates.append(" ".join(tokens[index:index + width]))
    return candidates


def _chinese_term_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    for segment in CHINESE_SEGMENT_RE.findall(text):
        if segment in THEME_STOPWORDS_ZH:
            continue
        if 2 <= len(segment) <= 8:
            candidates.append(segment)
        for width in (4, 3, 2):
            for index in range(len(segment) - width + 1):
                gram = segment[index:index + width]
                if gram in THEME_STOPWORDS_ZH:
                    continue
                candidates.append(gram)
    return candidates


def _theme_term_candidates(paper: dict[str, Any]) -> list[str]:
    text = _paper_text(paper)
    return _english_term_candidates(text) + _chinese_term_candidates(text)


def _theme_sort_key(term: str, paper_ids: tuple[str, ...], frequency: int) -> tuple[int, int, int, int, str]:
    token_count = len(term.split()) if " " in term else 1
    return (-len(paper_ids), -frequency, -token_count, -len(term), term)


def _is_redundant_theme_term(
    term: str,
    paper_ids: tuple[str, ...],
    selected: list[tuple[str, tuple[str, ...]]],
) -> bool:
    term_tokens = set(term.split())
    for existing_term, existing_paper_ids in selected:
        if paper_ids != existing_paper_ids:
            continue
        existing_tokens = set(existing_term.split())
        if term_tokens and term_tokens <= existing_tokens:
            return True
        if term in existing_term and len(term) < len(existing_term):
            return True
    return False


def build_text_themes(
    papers: list[dict[str, Any]],
    *,
    paper_id_key: str = "paper_id",
    max_themes: int = 8,
) -> dict[str, Any]:
    term_to_papers: dict[str, list[str]] = defaultdict(list)
    term_frequency: Counter[str] = Counter()
    for index, paper in enumerate(papers, 1):
        paper_id = str(paper.get(paper_id_key) or paper.get("id") or f"seed-{index}")
        for term in _theme_term_candidates(paper):
            term_to_papers[term].append(paper_id)
            term_frequency[term] += 1

    candidate_terms = sorted(
        (
            (term, tuple(sorted(set(paper_ids))))
            for term, paper_ids in term_to_papers.items()
            if term and paper_ids
        ),
        key=lambda item: _theme_sort_key(item[0], item[1], term_frequency[item[0]]),
    )

    selected_terms: list[tuple[str, tuple[str, ...]]] = []
    repeated_candidates = [item for item in candidate_terms if len(item[1]) >= 2]
    for term, paper_ids in repeated_candidates or candidate_terms:
        if _is_redundant_theme_term(term, paper_ids, selected_terms):
            continue
        selected_terms.append((term, paper_ids))
        if len(selected_terms) >= max_themes:
            break

    themes = [
        {
            "name": display_theme_name(term),
            "value": len(paper_ids),
            "paper_ids": list(paper_ids),
        }
        for term, paper_ids in selected_terms
    ]
    return {"themes": themes, "total_papers": len(papers)}
