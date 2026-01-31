"""Event period options: 1 hour, 8 hours, 24 hours, 1 week."""
from typing import Literal

EVENT_PERIODS: dict[str, int] = {
    "1h": 60,
    "8h": 480,
    "24h": 1440,
    "1w": 10080,
}

# Canonical market types: 1h (default) and 24h (optional). Used for propose flow.
CANONICAL_WINDOW_MINUTES: dict[str, int] = {
    "1h": 60,
    "24h": 1440,
}

PeriodValue = Literal["1h", "8h", "24h", "1w"]


def period_to_minutes(period: str) -> int:
    """Convert period string to minutes. Raises ValueError if invalid."""
    if period not in EVENT_PERIODS:
        raise ValueError(f"Invalid period: {period}. Must be one of: {list(EVENT_PERIODS.keys())}")
    return EVENT_PERIODS[period]


def market_type_to_minutes(market_type: str) -> int:
    """Return window minutes for canonical market type. Default 60 for unknown."""
    return CANONICAL_WINDOW_MINUTES.get(market_type, 60)
