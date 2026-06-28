"""Shared deterministic theme clustering helpers for report rendering."""

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
THEME_LEXICON_EN_PATH = Path(__file__).resolve().parent / "data" / "theme_lexicon.en.json"
THEME_LEXICON_ZH_PATH = Path(__file__).resolve().parent / "data" / "theme_lexicon.zh.json"
THEME_CONCEPT_ALIAS_INDEX_PATH = Path(__file__).resolve().parent / "data" / "theme_concept_alias_index.json"
THEME_CONCEPT_ALIASES_LEGACY_PATH = Path(__file__).resolve().parent / "data" / "theme_concept_aliases.json"
THEME_CONCEPT_ALIASES_PATH = THEME_CONCEPT_ALIASES_LEGACY_PATH



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
RAW_LOW_SIGNAL_STATUS = "low_signal_candidates"


def _singular_alias_token(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith(("ches", "shes", "sses", "xes", "zes")):
        return token[:-2]
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _normalize_concept_alias(value: str) -> str:
    text = (value or "").strip().casefold()
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        text = re.sub(r"(?<=[\u4e00-\u9fff])(?=[A-Za-z0-9])", " ", text)
        text = re.sub(r"(?<=[A-Za-z0-9])(?=[\u4e00-\u9fff])", " ", text)
        text = text.replace("∞", " infinity ")
        text = text.replace("&", " and ")
        text = re.sub(r"[\-_/]+", " ", text)
        text = re.sub(r"[^\w\s\u4e00-\u9fff]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()
    text = text.replace("∞", " infinity ")
    text = text.replace("&", " and ")
    text = re.sub(r"[\-_/]+", " ", text)
    text = re.sub(r"[^a-z0-9+\s]+", " ", text)
    tokens = [_singular_alias_token(token) for token in text.split() if token]
    return " ".join(tokens)


def _load_theme_concept_aliases(
    *,
    index_path: Path = THEME_CONCEPT_ALIAS_INDEX_PATH,
    legacy_path: Path = THEME_CONCEPT_ALIASES_LEGACY_PATH,
) -> dict[str, dict[str, Any]]:
    index_path = Path(index_path)
    if index_path.exists():
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        concepts = payload.get("concepts") or {}
        aliases = payload.get("aliases") or {}
        alias_index: dict[str, dict[str, Any]] = {}
        for alias_key, concept_id in aliases.items():
            concept = concepts.get(str(concept_id))
            if isinstance(concept, dict):
                alias_index.setdefault(str(alias_key), concept)
        return alias_index

    legacy_path = Path(legacy_path)
    if not legacy_path.exists():
        return {}
    payload = json.loads(legacy_path.read_text(encoding="utf-8"))
    alias_index: dict[str, dict[str, Any]] = {}
    for concept in payload.get("concept_aliases") or []:
        if not isinstance(concept, dict):
            continue
        aliases = concept.get("aliases") or {}
        for lang in ("en", "zh"):
            for alias in aliases.get(lang) or []:
                normalized = _normalize_concept_alias(str(alias))
                if not normalized:
                    continue
                # Materialization removes accepted alias conflicts; keep first
                # value stable if a future partial artifact contains a duplicate.
                alias_index.setdefault(f"{lang}:{normalized}", concept)
    return alias_index


THEME_CONCEPT_ALIAS_INDEX = _load_theme_concept_aliases()


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


def _is_chinese_term(term: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in term or "")


def _build_chinese_concept_alias_terms() -> tuple[str, ...]:
    terms = set()
    for alias_key in THEME_CONCEPT_ALIAS_INDEX:
        if not str(alias_key).startswith("zh:"):
            continue
        term = str(alias_key)[3:]
        if not (4 <= len(term) <= 20):
            continue
        if not _is_chinese_term(term):
            continue
        if _is_noisy_theme_term(term) or not _is_valid_chinese_theme_candidate(term):
            continue
        terms.add(term)
    return tuple(sorted(terms, key=lambda item: (-len(item), item)))


THEME_CONCEPT_ALIAS_ZH_TERMS = _build_chinese_concept_alias_terms()


def _compact_chinese_alias_text(value: str) -> str:
    compact = re.sub(r"[^\w\u4e00-\u9fff]+", "", (value or "").casefold())
    return compact.replace("_", "")


def _contains_latin_or_digit(value: str) -> bool:
    return bool(re.search(r"[a-z0-9]", value or ""))


def _is_ascii_alnum(value: str) -> bool:
    return len(value) == 1 and (("a" <= value <= "z") or ("0" <= value <= "9"))


def _single_ascii_neighbor_token(text: str, index: int, *, step: int) -> str:
    if step < 0:
        cursor = index - 1
        while cursor >= 0 and text[cursor].isspace():
            cursor -= 1
        end = cursor + 1
        while cursor >= 0 and _is_ascii_alnum(text[cursor]):
            cursor -= 1
        return text[cursor + 1:end]

    cursor = index
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    start = cursor
    while cursor < len(text) and _is_ascii_alnum(text[cursor]):
        cursor += 1
    return text[start:cursor]


def _has_single_ascii_neighbor_token(text: str, start: int, end: int) -> bool:
    return (
        len(_single_ascii_neighbor_token(text, start, step=-1)) == 1
        or len(_single_ascii_neighbor_token(text, end, step=1)) == 1
    )


def _contains_normalized_alias(text: str, alias: str) -> bool:
    if not alias:
        return False
    if _contains_latin_or_digit(alias):
        for match in re.finditer(re.escape(alias), text):
            start, end = match.span()
            if start > 0 and _is_ascii_alnum(text[start - 1]):
                continue
            if end < len(text) and _is_ascii_alnum(text[end]):
                continue
            if _has_single_ascii_neighbor_token(text, start, end):
                continue
            return True
        return False
    return alias in text


def _chinese_concept_alias_matches(text: str) -> list[str]:
    if not _is_chinese_term(text):
        return []
    normalized_text = _normalize_concept_alias(text)
    compact_text = _compact_chinese_alias_text(text)
    return [
        term
        for term in THEME_CONCEPT_ALIAS_ZH_TERMS
        if (
            term in text
            or _contains_normalized_alias(normalized_text, term)
            or (not _contains_latin_or_digit(term) and term in compact_text)
        )
    ]


def _theme_term_candidates(paper: dict[str, Any]) -> list[str]:
    text = _paper_text(paper)
    return [
        term
        for term in (
            _english_term_candidates(text)
            + _chinese_concept_alias_matches(text)
            + _chinese_term_candidates(text)
        )
        if not _is_noisy_theme_term(term)
    ]


def _concept_alias_key(term: str) -> str:
    lang = "zh" if _is_chinese_term(term) else "en"
    return f"{lang}:{_normalize_concept_alias(term)}"


def _concept_display_name(concept: dict[str, Any]) -> str:
    canonical = concept.get("canonical") or {}
    en = str(canonical.get("en") or "").strip()
    zh = str(canonical.get("zh") or "").strip()
    if en and zh:
        return f"{display_theme_name(en)} / {zh}"
    if zh:
        return zh
    if en:
        return display_theme_name(en)
    return str(concept.get("concept_id") or "").strip()


def _concept_specificity(concept: dict[str, Any]) -> int:
    try:
        return int(concept.get("specificity") or 0)
    except (TypeError, ValueError):
        return 0


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


def _concept_sort_key(
    name: str,
    concept: dict[str, Any],
    paper_ids: tuple[str, ...],
    frequency: int,
) -> tuple[int, int, int, int, str]:
    return (-len(paper_ids), -_concept_specificity(concept), -frequency, -len(name), name)


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


def _is_redundant_with_selected_concept_alias(
    term: str,
    paper_ids: tuple[str, ...],
    selected_concepts: list[tuple[str, tuple[str, ...]]],
    concept_matched_aliases: dict[str, dict[str, set[str]]],
) -> bool:
    term_papers = set(paper_ids)
    for concept_id, concept_paper_ids in selected_concepts:
        if not term_papers.issubset(set(concept_paper_ids)):
            continue
        for aliases in concept_matched_aliases[concept_id].values():
            for alias in aliases:
                if not alias or term == alias:
                    continue
                if _is_chinese_term(term) and _is_chinese_term(alias) and term in alias:
                    return True
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


def _paper_candidate_items(
    paper: dict[str, Any],
    *,
    paper_id: str,
    corpus_has_chinese: bool,
) -> list[tuple[str, str, dict[str, Any] | None]]:
    items: list[tuple[str, str, dict[str, Any] | None]] = []
    for term in _theme_term_candidates(paper):
        if not _is_allowed_text_candidate_for_corpus(term, corpus_has_chinese):
            continue
        concept = THEME_CONCEPT_ALIAS_INDEX.get(_concept_alias_key(term)) if corpus_has_chinese else None
        if concept:
            items.append(("concept", term, concept))
        else:
            items.append(("term", term, None))
    return items


def _select_text_theme_candidates(
    candidate_terms: list[tuple[str, tuple[str, ...]]],
    term_frequency: Counter[str],
    *,
    max_themes: int,
    require_quality_gate: bool,
) -> tuple[list[tuple[str, tuple[str, ...]]], str]:
    selected_terms: list[tuple[str, tuple[str, ...]]] = []
    status = "ok"
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
    if not selected_terms and not require_quality_gate:
        for term, paper_ids in candidate_terms:
            if _is_redundant_theme_term(term, paper_ids, selected_terms):
                continue
            selected_terms.append((term, paper_ids))
            if len(selected_terms) >= max_themes:
                break
        if selected_terms:
            status = RAW_LOW_SIGNAL_STATUS
    return selected_terms, status if selected_terms else RAW_LOW_SIGNAL_STATUS


def build_text_themes(
    papers: list[dict[str, Any]],
    *,
    paper_id_key: str = "paper_id",
    max_themes: int = 8,
    apply_quality_gate: bool = True,
) -> dict[str, Any]:
    term_to_papers: dict[str, list[str]] = defaultdict(list)
    term_frequency: Counter[str] = Counter()
    concept_to_papers: dict[str, list[str]] = defaultdict(list)
    concept_frequency: Counter[str] = Counter()
    concept_by_id: dict[str, dict[str, Any]] = {}
    concept_matched_aliases: dict[str, dict[str, set[str]]] = defaultdict(lambda: {"en": set(), "zh": set()})
    corpus_has_chinese = any(_is_chinese_term(_paper_text(paper)) for paper in papers)
    for index, paper in enumerate(papers, 1):
        paper_id = str(paper.get(paper_id_key) or paper.get("id") or f"seed-{index}")
        for kind, term, concept in _paper_candidate_items(paper, paper_id=paper_id, corpus_has_chinese=corpus_has_chinese):
            if kind == "concept" and concept:
                concept_id = str(concept.get("concept_id") or "")
                if not concept_id:
                    continue
                concept_by_id[concept_id] = concept
                concept_to_papers[concept_id].append(paper_id)
                concept_frequency[concept_id] += 1
                lang = "zh" if _is_chinese_term(term) else "en"
                concept_matched_aliases[concept_id][lang].add(term)
            else:
                term_to_papers[term].append(paper_id)
                term_frequency[term] += 1

    concept_candidates = sorted(
        (
            (concept_id, tuple(sorted(set(paper_ids))))
            for concept_id, paper_ids in concept_to_papers.items()
            if concept_id and paper_ids
        ),
        key=lambda item: _concept_sort_key(
            _concept_display_name(concept_by_id[item[0]]),
            concept_by_id[item[0]],
            item[1],
            concept_frequency[item[0]],
        ),
    )

    candidate_terms = sorted(
        (
            (term, tuple(sorted(set(paper_ids))))
            for term, paper_ids in term_to_papers.items()
            if term and paper_ids
        ),
        key=lambda item: _theme_sort_key(item[0], item[1], term_frequency[item[0]]),
    )

    selected_concepts = concept_candidates[:max_themes]
    if selected_concepts:
        candidate_terms = [
            (term, paper_ids)
            for term, paper_ids in candidate_terms
            if not _is_redundant_with_selected_concept_alias(
                term,
                paper_ids,
                selected_concepts,
                concept_matched_aliases,
            )
        ]
    remaining_slots = max(0, max_themes - len(selected_concepts))
    selected_terms, raw_status = _select_text_theme_candidates(
        candidate_terms,
        term_frequency,
        max_themes=remaining_slots,
        require_quality_gate=apply_quality_gate,
    )

    concept_themes = [
        {
            "name": _concept_display_name(concept_by_id[concept_id]),
            "concept_id": concept_id,
            "value": len(paper_ids),
            "paper_ids": list(paper_ids),
            "matched_aliases": {
                lang: sorted(values)
                for lang, values in concept_matched_aliases[concept_id].items()
                if values
            },
            "method": "concept_alias_text_fallback",
        }
        for concept_id, paper_ids in selected_concepts
    ]
    term_themes = [
        {
            "name": display_theme_name(term),
            "value": len(paper_ids),
            "paper_ids": list(paper_ids),
        }
        for term, paper_ids in selected_terms
    ]
    themes = concept_themes + term_themes
    if apply_quality_gate:
        themes, status = _apply_text_theme_quality_gate(themes, len(papers))
    else:
        _, gate_status = _apply_text_theme_quality_gate(themes, len(papers))
        status = RAW_LOW_SIGNAL_STATUS if themes and gate_status != "ok" else ("ok" if themes else raw_status)
    result = {"themes": themes, "total_papers": len(papers), "method": "text_frequency_fallback"}
    if status != "ok":
        result["status"] = status
        result["note"] = (
            "Text-derived raw candidates were kept for audit but too generic "
            "for reliable display topic grouping."
            if not apply_quality_gate and status == RAW_LOW_SIGNAL_STATUS
            else "Text-derived theme signal was too generic for reliable topic grouping."
        )
    return result
