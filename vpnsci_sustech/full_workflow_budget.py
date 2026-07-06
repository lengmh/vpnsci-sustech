"""Full paper-search-pro tier budgets shared by handoff and tests."""

from __future__ import annotations


FULL_TIER_BUDGETS: dict[str, int] = {
    "quick": 60,
    "standard": 180,
    "deep": 400,
    "audit": 1000,
}


def resolve_full_tier_budget(tier: str) -> int:
    """Return the max-paper budget for a full workflow tier."""

    key = tier.strip().lower()
    try:
        return FULL_TIER_BUDGETS[key]
    except KeyError as exc:
        valid = ", ".join(sorted(FULL_TIER_BUDGETS))
        raise ValueError(f"Unknown full workflow tier: {tier!r}. Expected one of: {valid}.") from exc


def format_budget_stop_reason(tier: str) -> str:
    """Format the shared budget stop reason for execution logs."""

    return f"budget_max_papers ({resolve_full_tier_budget(tier)})"
