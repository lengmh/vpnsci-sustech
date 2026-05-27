"""Search cache and session persistence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from uuid import uuid4

from .search_models import SearchError, SearchHit


@dataclass
class SearchSession:
    """Saved search request, result set, and decision metadata."""

    session_id: str
    query: str
    filters: dict
    hits: list[SearchHit]
    source_summary: dict[str, int] = field(default_factory=dict)
    errors: list[SearchError] = field(default_factory=list)
    upgrade_suggested: bool = False
    decision_reasons: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def new_session_id() -> str:
    return f"search-{uuid4().hex[:12]}"


def cache_key(source: str, query: str, filters: dict) -> str:
    payload = json.dumps(
        {"source": source.lower(), "query": query, "filters": filters},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _session_dir(cache_dir: Path) -> Path:
    return cache_dir / "search" / "sessions"


def _entries_dir(cache_dir: Path) -> Path:
    return cache_dir / "search" / "entries"


def save_session(session: SearchSession, cache_dir: Path) -> Path:
    directory = _session_dir(cache_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{session.session_id}.json"
    path.write_text(json.dumps(asdict(session), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_session(session_id: str, cache_dir: Path) -> SearchSession:
    path = _session_dir(cache_dir) / f"{session_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return SearchSession(
        session_id=data["session_id"],
        query=data["query"],
        filters=data.get("filters") or {},
        hits=[SearchHit(**item) for item in data.get("hits", [])],
        source_summary=data.get("source_summary") or {},
        errors=[SearchError(**item) for item in data.get("errors", [])],
        upgrade_suggested=bool(data.get("upgrade_suggested")),
        decision_reasons=data.get("decision_reasons") or [],
        created_at=data.get("created_at") or "",
    )


def save_cached_hits(source: str, query: str, filters: dict, hits: list[SearchHit], cache_dir: Path) -> Path:
    """Persist source-level search hits for a specific source/query/filter key."""

    directory = _entries_dir(cache_dir)
    directory.mkdir(parents=True, exist_ok=True)
    key = cache_key(source, query, filters)
    path = directory / f"{key}.json"
    payload = {
        "source": source,
        "query": query,
        "filters": filters,
        "created_at_epoch": time.time(),
        "hits": [asdict(hit) for hit in hits],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_cached_hits(
    source: str,
    query: str,
    filters: dict,
    cache_dir: Path,
    *,
    ttl_seconds: int = 24 * 60 * 60,
) -> list[SearchHit] | None:
    """Load cached hits if present and not expired."""

    path = _entries_dir(cache_dir) / f"{cache_key(source, query, filters)}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    created_at = float(data.get("created_at_epoch") or 0)
    if ttl_seconds > 0 and time.time() - created_at > ttl_seconds:
        return None
    return [SearchHit(**item) for item in data.get("hits", [])]
