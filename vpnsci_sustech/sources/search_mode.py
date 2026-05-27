"""Standard-search vs professional-research boundary decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from .search_models import SearchError, SearchHit


STRONG_PRO_TRIGGERS: tuple[str, ...] = (
    "文献综述",
    "系统综述",
    "调研报告",
    "html 报告",
    "HTML 报告",
    "系统检索",
    "PRISMA",
    "literature review",
    "systematic review",
    "research report",
    "html report",
    "systematic search",
    "prisma",
)

HIGH_INTENT_NON_TRIGGERS: tuple[str, ...] = (
    "全面覆盖",
    "尽量全面",
    "深入研究",
    "不要漏关键论文",
    "多给一点",
    "最新",
    "高引",
    "2023 年以后",
    "deep research",
    "comprehensive review",
    "broad coverage",
    "survey",
)

SEVERE_ERROR_CODES = {"rate_limited", "backend_blocked", "request_failed"}


@dataclass
class ModeDecision:
    mode: str
    reasons: list[str] = field(default_factory=list)


@dataclass
class UpgradeDecision:
    show: bool
    reasons: list[str] = field(default_factory=list)


def _contains_phrase(query: str, phrase: str) -> bool:
    if re.search(r"[\u4e00-\u9fff]", phrase):
        return phrase.lower() in query.lower()
    return re.search(rf"\b{re.escape(phrase.lower())}\b", query.lower()) is not None


def is_strong_pro_trigger(query: str) -> bool:
    return any(_contains_phrase(query, phrase) for phrase in STRONG_PRO_TRIGGERS)


def classify_search_mode(query: str, explicit_args: dict | None = None) -> ModeDecision:
    explicit_args = explicit_args or {}
    requested_mode = (explicit_args.get("mode") or "").lower()
    if requested_mode in {"pro", "professional", "report"}:
        return ModeDecision("pro", ["explicit_mode_pro"])
    if is_strong_pro_trigger(query):
        return ModeDecision("pro", ["strong_pro_trigger"])
    return ModeDecision("standard", ["no_strong_trigger"])


def is_doi_query(query: str) -> bool:
    text = query.strip()
    text = re.sub(r"^https?://(dx\.)?doi\.org/", "", text, flags=re.I)
    text = re.sub(r"^doi:\s*", "", text, flags=re.I)
    return re.fullmatch(r"10\.\d{4,9}/\S+", text) is not None


def is_url_query(query: str) -> bool:
    return re.match(r"^https?://", query.strip(), flags=re.I) is not None


def is_precise_single_paper_query(query: str) -> bool:
    text = query.strip()
    if is_doi_query(text) or is_url_query(text):
        return True
    if re.search(r"[\u4e00-\u9fff]", text):
        return False
    words = re.findall(r"[A-Za-z0-9]+", text)
    if len(words) < 6:
        return False
    title_case_words = sum(1 for word in words if word[:1].isupper())
    return title_case_words >= max(4, len(words) // 2) and not any(
        _contains_phrase(text, phrase) for phrase in HIGH_INTENT_NON_TRIGGERS
    )


def should_show_upgrade_suggestion(
    query: str,
    results: list[SearchHit],
    errors: list[SearchError],
    *,
    is_standard_search: bool = True,
) -> UpgradeDecision:
    reasons: list[str] = []
    if not is_standard_search:
        return UpgradeDecision(False, ["not_standard_search"])
    if len(results) < 5:
        return UpgradeDecision(False, ["result_count<5"])
    reasons.append("result_count>=5")
    if is_doi_query(query):
        return UpgradeDecision(False, ["doi_query"])
    if is_url_query(query):
        return UpgradeDecision(False, ["url_query"])
    if is_precise_single_paper_query(query):
        return UpgradeDecision(False, ["precise_single_paper_query"])
    doi_or_url_count = sum(1 for hit in results if hit.doi or hit.url)
    if doi_or_url_count < 3:
        return UpgradeDecision(False, ["doi_or_url_count<3"])
    reasons.append("doi_or_url_count>=3")
    severe_errors = [err for err in errors if err.code in SEVERE_ERROR_CODES]
    if severe_errors:
        return UpgradeDecision(False, [f"severe_error:{severe_errors[0].code}"])
    reasons.append("no_severe_errors")
    return UpgradeDecision(True, reasons)
