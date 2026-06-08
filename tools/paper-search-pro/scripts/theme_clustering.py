"""Deterministic theme clustering helpers for report rendering.

Tool-local copy kept under `tools/paper-search-pro/scripts/` so the bundled
toolchain does not depend on importing `vpnsci_sustech.*` at runtime.
Behavior should stay aligned with the repo-level helper.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
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
    "thesis",
    "dissertation",
    "proceedings",
    "conference",
    "conferences",
    "symposium",
    "workshop",
    "university",
    "college",
    "school",
    "system",
    "systems",
    "their",
    "these",
    "via",
    "using",
    "we",
    "with",
}
THEME_LEXICON_EN_PATH = Path(__file__).resolve().parent.parent / "assets" / "theme_lexicon.en.json"
THEME_LEXICON_ZH_PATH = Path(__file__).resolve().parent.parent / "assets" / "theme_lexicon.zh.json"



def _load_theme_lexicon_en() -> dict[str, list[str]]:
    payload = json.loads(THEME_LEXICON_EN_PATH.read_text(encoding="utf-8"))
    required_keys = ("token_stopwords", "generic_label_terms")
    missing = [key for key in required_keys if key not in payload]
    if missing:
        raise ValueError(f"English theme lexicon missing keys: {', '.join(missing)}")
    return {key: [str(item).lower() for item in payload.get(key) or []] for key in required_keys}

def _load_theme_lexicon_zh() -> dict[str, list[str]]:
    payload = json.loads(THEME_LEXICON_ZH_PATH.read_text(encoding="utf-8"))
    required_keys = (
        "generic_terms",
        "connector_terms",
        "theme_shape_suffixes",
        "noise_substrings",
        "fragment_prefixes",
        "embedded_suffix_connectors",
    )
    missing = [key for key in required_keys if key not in payload]
    if missing:
        raise ValueError(f"Chinese theme lexicon missing keys: {', '.join(missing)}")
    return {key: [str(item) for item in payload.get(key) or []] for key in required_keys}


THEME_LEXICON_EN = _load_theme_lexicon_en()
THEME_LEXICON_ZH = _load_theme_lexicon_zh()
THEME_STOPWORDS_ZH = set(THEME_LEXICON_ZH["generic_terms"])
THEME_STOPWORDS_EN.update(THEME_LEXICON_EN["token_stopwords"])
THEME_GENERIC_LABELS_EN = set(THEME_LEXICON_EN["generic_label_terms"])
THEME_ACRONYMS = {"ai", "ct", "dna", "mri", "nlp", "pcr", "rna", "svm"}
ENGLISH_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9-]*")
CHINESE_SEGMENT_RE = re.compile(r"[\u4e00-\u9fff]{2,20}")
THEME_NOISE_SUBSTRINGS = (
    *THEME_LEXICON_ZH["noise_substrings"],
    "university",
    "college",
    "school",
    "proceedings",
    "conference",
    "symposium",
    "workshop",
    "thesis",
    "dissertation",
)
CHINESE_DOMAIN_SUFFIXES = tuple(THEME_LEXICON_ZH["theme_shape_suffixes"])
CHINESE_BOUNDARY_CHARS = set("，。；;：:、（）()[]【】<>《》!?！？\n\r\t ")
CHINESE_LINKER_TOKENS = tuple(THEME_LEXICON_ZH["connector_terms"])
CHINESE_FRAGMENT_PREFIXES = tuple(THEME_LEXICON_ZH["fragment_prefixes"])
CHINESE_EMBEDDED_SUFFIX_CONNECTORS = tuple(THEME_LEXICON_ZH["embedded_suffix_connectors"])
LOW_SIGNAL_STATUS = "insufficient_text_theme_signal"


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


def _is_noisy_theme_term(term: str) -> bool:
    normalized = (term or "").strip()
    if not normalized:
        return True
    lowered = normalized.lower()
    if lowered in THEME_STOPWORDS_EN or lowered in THEME_GENERIC_LABELS_EN or normalized in THEME_STOPWORDS_ZH:
        return True
    return any(noise in normalized or noise in lowered for noise in THEME_NOISE_SUBSTRINGS)


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
            if _is_noisy_theme_term(kw):
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
        for key in ("title", "abstract")
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


def _is_chinese_char(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff"


def _trim_chinese_phrase(raw: str) -> str:
    phrase = (raw or "").strip()
    changed = True
    while changed and phrase:
        changed = False
        for connector in CHINESE_LINKER_TOKENS:
            if phrase.startswith(connector) and len(phrase) - len(connector) >= 2:
                phrase = phrase[len(connector):]
                changed = True
            if phrase.endswith(connector) and len(phrase) - len(connector) >= 2:
                phrase = phrase[:-len(connector)]
                changed = True
        for stopword in sorted(THEME_STOPWORDS_ZH, key=len, reverse=True):
            if phrase.startswith(stopword) and len(phrase) - len(stopword) >= 2:
                phrase = phrase[len(stopword):]
                changed = True
            # Some words (for example 治疗) are too generic alone, but are
            # valid domain suffixes inside phrases such as 靶向放射性核素治疗.
            if (
                stopword not in CHINESE_DOMAIN_SUFFIXES
                and phrase.endswith(stopword)
                and len(phrase) - len(stopword) >= 2
            ):
                phrase = phrase[:-len(stopword)]
                changed = True
    return phrase.strip()


def _chinese_domain_phrases(text: str) -> list[str]:
    phrases: list[str] = []
    for suffix in CHINESE_DOMAIN_SUFFIXES:
        start = 0
        while True:
            hit = text.find(suffix, start)
            if hit < 0:
                break
            suffix_end = hit + len(suffix)
            left = hit
            while left > 0 and _is_chinese_char(text[left - 1]) and suffix_end - (left - 1) <= 12:
                left -= 1
            raw = text[left:suffix_end]
            for offset in range(0, max(1, min(5, len(raw) - len(suffix) + 1))):
                phrase = _trim_chinese_phrase(raw[offset:])
                if 4 <= len(phrase) <= 12 and phrase.endswith(suffix):
                    phrases.append(phrase)
            start = suffix_end
    return phrases


def _chinese_term_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    candidates.extend(_chinese_domain_phrases(text))
    for segment in CHINESE_SEGMENT_RE.findall(text):
        if segment in THEME_STOPWORDS_ZH:
            continue
        # Full short segments are often publication-grade phrases; raw 2-char
        # grams are too noisy and are only kept when no better phrase exists.
        if 4 <= len(segment) <= 12:
            candidate = _trim_chinese_phrase(segment)
            if _is_valid_chinese_theme_candidate(candidate):
                candidates.append(candidate)
        for width in (8, 6, 5, 4, 3):
            for index in range(len(segment) - width + 1):
                gram = _trim_chinese_phrase(segment[index:index + width])
                if gram in THEME_STOPWORDS_ZH:
                    continue
                if len(gram) >= 3 and _is_valid_chinese_theme_candidate(gram):
                    candidates.append(gram)
    return [candidate for candidate in candidates if candidate]


def _has_embedded_domain_connector(term: str) -> bool:
    for suffix in CHINESE_DOMAIN_SUFFIXES:
        start = 0
        while True:
            index = term.find(suffix, start)
            if index < 0:
                break
            suffix_end = index + len(suffix)
            if suffix_end < len(term) and any(
                term.startswith(connector, suffix_end)
                for connector in CHINESE_EMBEDDED_SUFFIX_CONNECTORS
            ):
                return True
            start = index + 1
    return False


def _is_valid_chinese_theme_candidate(term: str) -> bool:
    candidate = (term or "").strip()
    if not candidate:
        return False
    if candidate in THEME_STOPWORDS_ZH:
        return False
    for stopword in THEME_STOPWORDS_ZH:
        if candidate.startswith(stopword) and len(candidate) - len(stopword) <= 1:
            return False
        if (
            stopword not in CHINESE_DOMAIN_SUFFIXES
            and candidate.endswith(stopword)
            and len(candidate) - len(stopword) <= 1
        ):
            return False
    for suffix in CHINESE_DOMAIN_SUFFIXES:
        if candidate.endswith(suffix) and len(candidate) - len(suffix) < 2:
            return False
    if _has_embedded_domain_connector(candidate):
        return False
    return True


def _theme_term_candidates(paper: dict[str, Any]) -> list[str]:
    text = _paper_text(paper)
    return [
        term
        for term in (_english_term_candidates(text) + _chinese_term_candidates(text))
        if not _is_noisy_theme_term(term)
    ]


def _is_chinese_term(term: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in term or "")


def _theme_specificity(term: str) -> int:
    if _is_chinese_term(term):
        score = min(len(term), 12)
        if any(term.endswith(suffix) for suffix in CHINESE_DOMAIN_SUFFIXES):
            score += 6
        for linker in CHINESE_LINKER_TOKENS:
            if linker in term:
                score -= 4 if len(linker) > 1 else 2
        for suffix in CHINESE_DOMAIN_SUFFIXES:
            start = 0
            while True:
                index = term.find(suffix, start)
                if index < 0:
                    break
                suffix_end = index + len(suffix)
                if suffix_end < len(term) and any(
                    term.startswith(connector, suffix_end)
                    for connector in CHINESE_EMBEDDED_SUFFIX_CONNECTORS
                ):
                    score -= 6
                start = index + 1
        if term.startswith(CHINESE_FRAGMENT_PREFIXES):
            score -= 4
        if len(term) <= 2:
            score -= 8
        if term.startswith(CHINESE_FRAGMENT_PREFIXES):
            score -= 8
        return score
    token_count = len(term.split()) if " " in term else 1
    score = token_count * 4 + min(len(term), 20) // 4
    if term in {"machine", "learning", "image", "classification", "segmentation", "optimization"}:
        score -= 4
    return score


def _theme_sort_key(term: str, paper_ids: tuple[str, ...], frequency: int) -> tuple[int, int, int, int, str]:
    token_count = len(term.split()) if " " in term else 1
    return (-len(paper_ids), -_theme_specificity(term), -frequency, -token_count, term)


def _is_allowed_text_candidate_for_corpus(term: str, corpus_has_chinese: bool) -> bool:
    if not corpus_has_chinese:
        return True
    return _is_chinese_term(term) or " " in term


def _is_redundant_theme_term(
    term: str,
    paper_ids: tuple[str, ...],
    selected: list[tuple[str, tuple[str, ...]]],
) -> bool:
    term_tokens = set(term.split())
    for existing_term, existing_paper_ids in selected:
        same_or_subset = set(paper_ids).issubset(set(existing_paper_ids)) or set(existing_paper_ids).issubset(set(paper_ids))
        if not same_or_subset:
            continue
        existing_tokens = set(existing_term.split())
        if term_tokens and existing_tokens and term_tokens <= existing_tokens:
            return True
        if term in existing_term and len(term) < len(existing_term):
            return True
        if existing_term in term and len(existing_term) < len(term):
            continue
    return False


def _is_specific_theme_term(term: str) -> bool:
    if _is_noisy_theme_term(term):
        return False
    if _is_chinese_term(term):
        if any(linker in term for linker in CHINESE_LINKER_TOKENS):
            return False
        if term.startswith(CHINESE_FRAGMENT_PREFIXES):
            return False
        if len(term) == 3 and _theme_specificity(term) >= 3:
            return True
        return len(term) >= 4 and _theme_specificity(term) >= 6
    if " " in term:
        tokens = [token for token in term.lower().split() if token]
        return any(token not in THEME_GENERIC_LABELS_EN for token in tokens)
    return len(term) >= 5 and term.lower() not in THEME_GENERIC_LABELS_EN


def _apply_text_theme_quality_gate(themes: list[dict[str, Any]], total_papers: int) -> tuple[list[dict[str, Any]], str]:
    specific = [theme for theme in themes if _is_specific_theme_term(str(theme.get("name") or ""))]
    if not specific:
        return [], LOW_SIGNAL_STATUS
    repeated_specific = [theme for theme in specific if _has_repeated_theme_support(theme, total_papers)]
    if total_papers <= 2:
        return (repeated_specific[: max(1, len(repeated_specific))], "ok") if repeated_specific else ([], LOW_SIGNAL_STATUS)
    if len(repeated_specific) < min(2, total_papers):
        return [], LOW_SIGNAL_STATUS
    return specific, "ok"


def _has_repeated_theme_support(theme: dict[str, Any], total_papers: int) -> bool:
    value = int(theme.get("value") or 0)
    if value < 2:
        return False
    name = str(theme.get("name") or "")
    if total_papers > 2 and _is_chinese_term(name) and len(name) <= 3:
        min_short_term_support = min(total_papers, max(3, (total_papers + 4) // 5))
        if value < min_short_term_support:
            return False
    return True


def build_text_themes(
    papers: list[dict[str, Any]],
    *,
    paper_id_key: str = "paper_id",
    max_themes: int = 8,
) -> dict[str, Any]:
    term_to_papers: dict[str, list[str]] = defaultdict(list)
    term_frequency: Counter[str] = Counter()
    corpus_has_chinese = any(_is_chinese_term(_paper_text(paper)) for paper in papers)
    for index, paper in enumerate(papers, 1):
        paper_id = str(paper.get(paper_id_key) or paper.get("id") or f"seed-{index}")
        for term in _theme_term_candidates(paper):
            if not _is_allowed_text_candidate_for_corpus(term, corpus_has_chinese):
                continue
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
    repeated_candidates = [
        item for item in candidate_terms
        if len(item[1]) >= 2 and _is_specific_theme_term(item[0])
    ]
    high_specificity_singletons = [
        item for item in candidate_terms
        if len(item[1]) == 1 and _is_specific_theme_term(item[0]) and _theme_specificity(item[0]) >= 10
    ]
    for term, paper_ids in repeated_candidates:
        if _is_redundant_theme_term(term, paper_ids, selected_terms):
            continue
        selected_terms.append((term, paper_ids))
        if len(selected_terms) >= max_themes:
            break
    for term, paper_ids in high_specificity_singletons:
        if _is_redundant_theme_term(term, paper_ids, selected_terms):
            continue
        selected_terms.append((term, paper_ids))
        if len(selected_terms) >= max_themes:
            break
    if not selected_terms:
        for term, paper_ids in candidate_terms:
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
    themes, status = _apply_text_theme_quality_gate(themes, len(papers))
    result = {"themes": themes, "total_papers": len(papers), "method": "text_frequency_fallback"}
    if status != "ok":
        result["status"] = status
        result["note"] = "Text-derived theme signal was too generic for reliable topic grouping."
    return result
