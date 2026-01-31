"""
Attention Index pipeline: collect activity from channels/tools, compute delta, normalize, combine.
Index(t) = 100 + 10 * sum(weight * normalized_delta)
"""
import asyncio
import math
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import feedparser

# Weights per channel (must sum to 1 for scaling)
CHANNEL_WEIGHTS = {"Hacker News": 0.35, "Reddit": 0.35, "GitHub": 0.15, "LinkedIn": 0.15}


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
    return 0.0


def fetch_github_activity(keywords: list[str], exclusions: list[str]) -> float:
    """Placeholder: GitHub API; real impl TBD (repos, stars, etc.)."""
    return 0.0


def fetch_linkedin_activity(keywords: list[str], exclusions: list[str]) -> float:
    """Placeholder: LinkedIn events/posts; real impl TBD."""
    return 0.0


# Map tool id -> (channel_display_name, fetcher_fn) for agent-selected tools
def _get_tool_fetchers() -> dict[str, tuple[str, Callable[[list[str], list[str]], float]]]:
    return {
        "hn_frontpage": ("Hacker News", fetch_hn_activity),
        "reddit": ("Reddit", fetch_reddit_activity),
        "github": ("GitHub", fetch_github_activity),
        "linkedin": ("LinkedIn", fetch_linkedin_activity),
    }


async def build_index(event_id: str, config: dict) -> tuple[float, dict]:
    """
    Run the index pipeline for this event: compute_index and store snapshot.
    Returns (index_value, activity) for use in accept decision.
    Placeholder: waits forever so the propose request hangs (infinite load).
    """
    await asyncio.Event().wait()
    from backend.src.db import queries as db
    index_value, activity = compute_index(config, None, None)
    await db.add_index_snapshot(event_id, get_iso_now(), index_value)
    await db.update_event_index(event_id, index_value)
    return index_value, activity


def log_scale(x: float) -> float:
    if x <= 0:
        return 0.0
    return math.log1p(x)


def _get_fetchers_for_config(config: dict) -> list[tuple[str, Callable[[list[str], list[str]], float]]]:
    """Return list of (channel_name, fetcher_fn) from config: prefer tools, else channels."""
    tools = config.get("tools")
    fetchers_map = _get_tool_fetchers()
    if tools:
        return [fetchers_map[tid] for tid in tools if tid in fetchers_map]
    channels = config.get("channels", ["Hacker News", "Reddit"])
    name_to_fetcher = {
        "Hacker News": fetch_hn_activity,
        "Reddit": fetch_reddit_activity,
        "GitHub": fetch_github_activity,
        "LinkedIn": fetch_linkedin_activity,
    }
    return [(ch, name_to_fetcher[ch]) for ch in channels if ch in name_to_fetcher]


def compute_index(
    config: dict,
    previous_activity: Optional[dict] = None,
    current_activity: Optional[dict] = None,
) -> tuple:
    """
    Compute index from current activity and previous. Returns (index_value, current_activity_for_next_round).
    Baseline should set index_start = 100; subsequent calls use deltas.
    Prefers config.tools (agent-selected); falls back to config.channels.
    """
    keywords = config.get("keywords", [])
    exclusions = config.get("exclusions", [])
    fetchers = _get_fetchers_for_config(config)

    activity = {}
    for channel_name, fetcher_fn in fetchers:
        activity[channel_name] = fetcher_fn(keywords, exclusions)

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
