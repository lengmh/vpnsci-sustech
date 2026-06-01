"""Backend routing helpers for explicit and high-confidence source requests."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BackendRoute:
    backend: str = ""
    reasons: list[str] = field(default_factory=list)
    explicit: bool = False


_CNKI_EXPLICIT_TERMS = [
    "cnki",
    "知网",
    "中国知网",
]

_CNKI_DATABASE_TERMS = [
    "硕博论文",
    "硕士论文",
    "博士论文",
    "学位论文",
    "中文核心",
    "北大核心",
    "cssci",
    "cscd",
    "核心期刊",
    "中文期刊",
]


def resolve_requested_backend(query: str, explicit_backend: str = "") -> BackendRoute:
    """Resolve requested backend without treating plain Chinese as CNKI intent."""

    backend = (explicit_backend or "").strip().lower()
    if backend:
        return BackendRoute(backend=backend, reasons=["explicit_backend"], explicit=True)

    text = (query or "").strip().lower()
    for term in _CNKI_EXPLICIT_TERMS:
        if term.lower() in text:
            return BackendRoute(backend="cnki", reasons=[f"cnki_intent:{term}"])

    for term in _CNKI_DATABASE_TERMS:
        if term.lower() in text:
            return BackendRoute(backend="cnki", reasons=[f"cnki_database_intent:{term}"])

    return BackendRoute()
