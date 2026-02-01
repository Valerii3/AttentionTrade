"""
Attention Index pipeline: collect activity from channels/tools, compute delta, normalize, combine.
Index(t) = 100 + 10 * sum(weight * normalized_delta)

The Attention Index is the oracle: it is defined once per event (by config and channel data only),
is public and fixed, and is used only for resolution, explanation, and auditability.
Trading does not affect the index. For demo events, the index may be synthetic (see demo_index).
"""
import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Optional

import httpx

# Weights per channel (must sum to 1 for scaling)
CHANNEL_WEIGHTS = {
    "Hacker News": 0.30,
    "Reddit": 0.25,
    "YouTube": 0.25,
    "GitHub": 0.10,
    "LinkedIn": 0.10,
}

ALGOLIA_HN_SEARCH = "https://hn.algolia.com/api/v1/search_by_date"
HN_SEARCH_TIMEOUT = 20.0
HN_HITS_PER_PAGE = 100

# Tech channels use 30-day lookback for index build; HN cap
HN_LOOKBACK_DAYS_TECH = 30

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_SEARCH_TIMEOUT = 15.0
YOUTUBE_MAX_VIDEOS = 25

logger = logging.getLogger(__name__)


def _unix_ts_days_ago(days: int) -> int:
    return int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())


def fetch_hn_activity(
    keywords: list[str],
    exclusions: list[str],
    config: Optional[dict] = None,
) -> float:
    """
    Fetch HN activity via Algolia search_by_date. Score = sum over hits of engagement:
    log1p(points) + 0.5*log1p(num_comments). For tech we use 30-day lookback; otherwise up to 7 days.
    """
    if not keywords:
        return 0.0
    config = config or {}
    window_minutes = config.get("window_minutes", 1440)
    # Tech: use last month (30 days) for index build; 1h window still gets 30 days of HN data
    days = min(HN_LOOKBACK_DAYS_TECH, max(1, window_minutes // 1440)) if window_minutes >= 1440 else HN_LOOKBACK_DAYS_TECH
    query = " ".join(kw[:50] for kw in keywords[:5]).strip() or keywords[0]
    exclusions_lower = [e.lower() for e in exclusions] if exclusions else []

    try:
        params = {
            "query": query,
            "tags": "story",
            "numericFilters": f"created_at_i>={_unix_ts_days_ago(days)}",
            "hitsPerPage": HN_HITS_PER_PAGE,
        }
        with httpx.Client(timeout=HN_SEARCH_TIMEOUT) as client:
            r = client.get(ALGOLIA_HN_SEARCH, params=params)
            r.raise_for_status()
        data = r.json()
        hits = data.get("hits", [])

        score = 0.0
        for h in hits:
            title = (h.get("title") or h.get("comment_text") or "").lower()
            url = (h.get("url") or "").lower()
            if any(exc in title or exc in url for exc in exclusions_lower):
                continue
            points = h.get("points") or 0
            num_comments = h.get("num_comments") or 0
            # Engagement formula: points + comments (log-scaled)
            score += math.log1p(max(0, points)) + 0.5 * math.log1p(max(0, num_comments))
        return round(score, 4)
    except Exception as e:
        logger.warning("HN Algolia fetch failed: %s", e)
        return 0.0


def fetch_reddit_activity(
    keywords: list[str], exclusions: list[str], config: Optional[dict] = None
) -> float:
    """Placeholder: Reddit API often needs API key. Return 0 or mock for demo."""
    return 0.0


def fetch_github_activity(
    keywords: list[str], exclusions: list[str], config: Optional[dict] = None
) -> float:
    """Placeholder: GitHub API; real impl TBD (repos, stars, etc.)."""
    return 0.0


def fetch_linkedin_activity(
    keywords: list[str], exclusions: list[str], config: Optional[dict] = None
) -> float:
    """Placeholder: LinkedIn events/posts; real impl TBD."""
    return 0.0


def fetch_youtube_activity(
    keywords: list[str],
    exclusions: list[str],
    config: Optional[dict] = None,
) -> float:
    """
    Fetch YouTube activity via Data API v3. Score = sum over videos (last 30 days) of
    engagement: log1p(views) + log1p(likes) + 2*log1p(commentCount). Requires YOUTUBE_API_KEY.
    """
    import os
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not keywords:
        return 0.0
    config = config or {}
    query = " ".join(kw[:50] for kw in keywords[:5]).strip() or keywords[0]
    published_after = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        with httpx.Client(timeout=YOUTUBE_SEARCH_TIMEOUT) as client:
            search_r = client.get(
                f"{YOUTUBE_API_BASE}/search",
                params={
                    "part": "id",
                    "q": query,
                    "type": "video",
                    "publishedAfter": published_after,
                    "maxResults": YOUTUBE_MAX_VIDEOS,
                    "key": api_key,
                },
            )
            search_r.raise_for_status()
        search_data = search_r.json()
        video_ids = [item["id"]["videoId"] for item in search_data.get("items", []) if item.get("id", {}).get("videoId")]
        if not video_ids:
            return 0.0
        with httpx.Client(timeout=YOUTUBE_SEARCH_TIMEOUT) as client:
            stats_r = client.get(
                f"{YOUTUBE_API_BASE}/videos",
                params={
                    "part": "statistics",
                    "id": ",".join(video_ids[:25]),
                    "key": api_key,
                },
            )
            stats_r.raise_for_status()
        stats_data = stats_r.json()
        score = 0.0
        for item in stats_data.get("items", []):
            s = item.get("statistics", {})
            views = int(s.get("viewCount") or 0)
            likes = int(s.get("likeCount") or 0)
            comments = int(s.get("commentCount") or 0)
            score += math.log1p(views) + math.log1p(likes) + 2.0 * math.log1p(comments)
        return round(score, 4)
    except Exception as e:
        logger.warning("YouTube API fetch failed: %s", e)
        return 0.0


# Map tool id -> (channel_display_name, fetcher_fn) for agent-selected tools
def _get_tool_fetchers() -> dict[str, tuple[str, Callable[..., float]]]:
    return {
        "hn_frontpage": ("Hacker News", fetch_hn_activity),
        "reddit": ("Reddit", fetch_reddit_activity),
        "youtube": ("YouTube", fetch_youtube_activity),
        "github": ("GitHub", fetch_github_activity),
        "linkedin": ("LinkedIn", fetch_linkedin_activity),
    }


async def build_index(event_id: str, config: dict) -> tuple[float, dict]:
    """
    Run the index pipeline for this event: compute_index and store snapshot.
    Returns (index_value, activity) for use in accept decision.
    """
    from backend.src.db import queries as db

    index_value, activity = compute_index(config, None, None)
    t = get_iso_now()
    await db.add_index_snapshot(event_id, t, index_value)
    await db.update_event_index(event_id, index_value)
    return index_value, activity


def log_scale(x: float) -> float:
    if x <= 0:
        return 0.0
    return math.log1p(x)


def _get_fetchers_for_config(config: dict) -> list[tuple[str, Callable[..., float]]]:
    """Return list of (channel_name, fetcher_fn) from config: prefer tools, else channels."""
    tools = config.get("tools")
    fetchers_map = _get_tool_fetchers()
    if tools:
        return [fetchers_map[tid] for tid in tools if tid in fetchers_map]
    channels = config.get("channels", ["Hacker News", "Reddit"])
    name_to_fetcher = {
        "Hacker News": fetch_hn_activity,
        "Reddit": fetch_reddit_activity,
        "YouTube": fetch_youtube_activity,
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
    Uses only config and channel fetchers; no trade/position input. Baseline: index_start = 100; subsequent calls use deltas.
    Prefers config.tools (agent-selected); falls back to config.channels.
    """
    keywords = config.get("keywords", [])
    exclusions = config.get("exclusions", [])
    fetchers = _get_fetchers_for_config(config)

    activity = {}
    for channel_name, fetcher_fn in fetchers:
        activity[channel_name] = fetcher_fn(keywords, exclusions, config)

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


def parse_iso_utc(iso_str: str) -> datetime:
    """Parse ISO 8601 string to UTC datetime for reliable comparison (handles Z and +00:00)."""
    s = iso_str.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).astimezone(timezone.utc)
