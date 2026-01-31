"""
Attention Index pipeline: collect activity from channels, compute delta, normalize, combine.
Index(t) = 100 + 10 * sum(weight * normalized_delta)
"""
import math
import os
from datetime import datetime, timezone
from typing import Any, Optional

import feedparser

# Weights per channel (must sum to 1 for scaling)
CHANNEL_WEIGHTS = {"Hacker News": 0.6, "Reddit": 0.4}


def fetch_hn_activity(keywords: list[str], exclusions: list[str]) -> float:
    """Fetch HN front page RSS and count matching items. Returns a simple activity score."""
    try:
        feed = feedparser.parse(
            "https://hnrss.org/frontpage",
            request_headers={"User-Agent": "AttentionMarkets/1.0"},
        )
        score = 0.0
        for entry in feed.entries[:30]:
            title = (entry.get("title") or "").lower()
            # Exclude first
            if any(exc.lower() in title for exc in exclusions):
                continue
            if any(kw.lower() in title for kw in keywords):
                score += 1.0
        return score
    except Exception:
        return 0.0


def fetch_reddit_activity(keywords: list[str], exclusions: list[str]) -> float:
    """Placeholder: Reddit API often needs API key. Return 0 or mock for demo."""
    # For hackathon we can use a simple placeholder; real impl would use Reddit API
    return 0.0


def log_scale(x: float) -> float:
    if x <= 0:
        return 0.0
    return math.log1p(x)


def compute_index(
    config: dict,
    previous_activity: Optional[dict] = None,
    current_activity: Optional[dict] = None,
) -> tuple:
    """
    Compute index from current activity and previous. Returns (index_value, current_activity_for_next_round).
    Baseline should set index_start = 100; subsequent calls use deltas.
    """
    keywords = config.get("keywords", [])
    exclusions = config.get("exclusions", [])
    channels = config.get("channels", ["Hacker News", "Reddit"])

    activity = {}
    if "Hacker News" in channels:
        activity["Hacker News"] = fetch_hn_activity(keywords, exclusions)
    if "Reddit" in channels:
        activity["Reddit"] = fetch_reddit_activity(keywords, exclusions)

    if previous_activity is None:
        # First run: treat as baseline, index = 100
        return 100.0, activity

    # Delta per channel, log-scaled
    deltas = {}
    for ch in activity:
        prev = previous_activity.get(ch, 0.0)
        delta_raw = max(0.0, activity[ch] - prev)
        deltas[ch] = log_scale(delta_raw)

    # Normalize (simple: cap and scale)
    total_delta = 0.0
    for ch, w in CHANNEL_WEIGHTS.items():
        if ch in deltas:
            d = min(deltas[ch], 5.0)  # cap
            total_delta += w * d

    # Index = 100 + 10 * total_delta (so small moves give ~100–110)
    index = 100.0 + 10.0 * total_delta
    return round(index, 2), activity


def get_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()
