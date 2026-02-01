"""
Aggregate raw index_snapshots into time buckets for chart time dimensions (1h, 6h, 1d, 1w, 1m).
Returns one point per bucket (last value in bucket = close).
"""
from datetime import datetime, timezone
from typing import Optional

# Interval name -> bucket size in seconds
INTERVAL_SECONDS = {
    "1h": 3600,
    "6h": 21600,
    "1d": 86400,
    "1w": 604800,
    "1m": 2592000,  # ~30 days
}


def _parse_iso(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def aggregate_history(
    raw: list[dict],
    interval: str,
    window_start_iso: Optional[str] = None,
) -> list[dict]:
    """
    Bucket raw snapshots by interval. Each bucket emits one point { t, index } with last value (close).
    raw: list of { "t": "ISO8601", "index": float }
    interval: one of "1h", "6h", "1d", "1w", "1m"
    window_start_iso: optional; if provided, bucket boundaries align to this time.
    """
    if not raw or interval not in INTERVAL_SECONDS:
        return raw
    bucket_seconds = INTERVAL_SECONDS[interval]

    # Alignment epoch: window start or first snapshot
    if window_start_iso:
        try:
            align_ts = _parse_iso(window_start_iso).timestamp()
        except (ValueError, TypeError):
            align_ts = _parse_iso(raw[0]["t"]).timestamp()
    else:
        align_ts = _parse_iso(raw[0]["t"]).timestamp()

    buckets: dict[int, tuple[str, float]] = {}  # bucket_key -> (last_t, last_index)
    for point in raw:
        t_str = point["t"]
        index_val = point["index"]
        try:
            ts = _parse_iso(t_str).timestamp()
        except (ValueError, TypeError):
            continue
        # Floor to bucket boundary aligned to align_ts
        bucket_key = int((ts - align_ts) // bucket_seconds) * bucket_seconds + int(align_ts)
        buckets[bucket_key] = (t_str, index_val)

    # Sort by bucket start, emit last (t, index) per bucket
    out = []
    for key in sorted(buckets.keys()):
        t_str, index_val = buckets[key]
        out.append({"t": t_str, "index": index_val})
    return out
