"""Derived search-session helpers."""

from __future__ import annotations

from dataclasses import replace

from .search_cache import SearchSession, new_session_id
from .search_models import SearchHit, coerce_search_hit


def derive_search_session(
    session: SearchSession,
    *,
    selected_hit_keys: list[str],
    derivation_type: str,
    derivation_note: str = "",
) -> SearchSession:
    """Create a derived SearchSession from selected hit identities."""

    selected_set = {value for value in (selected_hit_keys or []) if value}
    selected_hits: list[SearchHit] = []
    for hit in session.hits:
        coerced = coerce_search_hit(hit)
        if coerced.hit_key in selected_set:
            selected_hits.append(coerced)

    existing = session.derivation if isinstance(session.derivation, dict) else {}
    root_session_id = existing.get("root_session_id") or session.session_id
    derivation = {
        "source_session_id": session.session_id,
        "root_session_id": root_session_id,
        "derivation_type": derivation_type,
        "derivation_note": derivation_note,
        "selected_count_before": len(session.hits),
        "selected_count_after": len(selected_hits),
    }
    return SearchSession(
        session_id=new_session_id(),
        query=session.query,
        filters=dict(session.filters or {}),
        hits=[replace(hit) for hit in selected_hits],
        schema_version=session.schema_version or 2,
        origin=dict(session.origin or {}),
        derivation=derivation,
        display_query=session.display_query or session.query,
        recovered_label=session.recovered_label or "",
        source_summary=dict(session.source_summary or {}),
        errors=list(session.errors or []),
        upgrade_suggested=session.upgrade_suggested,
        decision_reasons=list(session.decision_reasons or []),
        created_at=session.created_at,
    )
