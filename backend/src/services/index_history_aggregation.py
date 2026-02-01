"""
Aggregate raw index_snapshots into time buckets for chart time dimensions (1h, 6h, 1d, 1w, 1m).
Returns one point per bucket (last value in bucket = close).
Also provides interpolation for sparse data to create smoother charts.
"""
import hashlib
import math
from datetime import datetime, timezone
from typing import Optional

# Interval name -> bucket size in seconds
INTERVAL_SECONDS = {
    "1h": 3600,
    "6h": 21600,
    "1d": 86400,
    "1w": 604800,
    "1m": 2592000,  # ~30 days
    "6m": 2592000,  # monthly buckets for 6-month view
}

# Target number of points per interval for smooth charts
TARGET_POINTS = {
    "1h": 12,   # 5 min spacing
    "6h": 24,   # 15 min spacing
    "1d": 24,   # 1 hour spacing
    "1w": 28,   # 6 hour spacing
    "1m": 30,   # 1 day spacing
    "6m": 26,   # ~1 week spacing
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
    interval: one of "1h", "6h", "1d", "1w", "1m", "6m"
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


def _deterministic_noise(seed: int, step: int) -> float:
    """Generate deterministic noise in range [-0.5, 0.5] based on seed and step."""
    h = hashlib.md5(f"{seed}-{step}".encode()).hexdigest()
    return (int(h[:8], 16) / 0xFFFFFFFF) - 0.5


def interpolate_history(
    raw: list[dict],
    interval: str,
    event_id: Optional[str] = None,
) -> list[dict]:
    """
    If raw has fewer points than target for the interval, interpolate to create smoother curve.
    Uses linear interpolation between actual points with small deterministic noise for realism.
    
    raw: list of { "t": "ISO8601", "index": float }
    interval: one of "1h", "6h", "1d", "1w", "1m", "6m"
    event_id: optional; used for deterministic noise seed
    """
    target = TARGET_POINTS.get(interval, 20)
    
    # If we have enough points or no points, return as-is
    if len(raw) >= target or len(raw) < 2:
        return raw
    
    # Parse timestamps and values
    points = []
    for p in raw:
        try:
            ts = _parse_iso(p["t"]).timestamp()
            points.append((ts, p["index"], p["t"]))
        except (ValueError, TypeError):
            continue
    
    if len(points) < 2:
        return raw
    
    # Sort by timestamp
    points.sort(key=lambda x: x[0])
    
    # Calculate how many points we need to add between existing points
    total_gaps = len(points) - 1
    points_to_add = target - len(points)
    points_per_gap = max(1, points_to_add // total_gaps) if total_gaps > 0 else 0
    
    # Seed for deterministic noise
    seed = int(hashlib.md5((event_id or "default").encode()).hexdigest()[:8], 16)
    
    result = []
    step = 0
    
    for i in range(len(points) - 1):
        ts1, val1, t_str1 = points[i]
        ts2, val2, _ = points[i + 1]
        
        # Add the original point
        result.append({"t": t_str1, "index": val1})
        
        # Calculate number of interpolated points for this gap
        # Distribute remaining points evenly, with more points in larger gaps
        gap_duration = ts2 - ts1
        total_duration = points[-1][0] - points[0][0]
        gap_ratio = gap_duration / total_duration if total_duration > 0 else 1.0 / total_gaps
        num_interp = max(1, int(points_to_add * gap_ratio))
        num_interp = min(num_interp, points_per_gap + 2)  # Cap to avoid too many in one gap
        
        # Generate interpolated points
        for j in range(1, num_interp + 1):
            t_frac = j / (num_interp + 1)
            interp_ts = ts1 + (ts2 - ts1) * t_frac
            
            # Linear interpolation with smooth easing
            eased_frac = t_frac  # Could use smoothstep for smoother curves
            base_val = val1 + (val2 - val1) * eased_frac
            
            # Add small deterministic noise (±0.3)
            noise = _deterministic_noise(seed, step) * 0.6
            interp_val = round(base_val + noise, 2)
            
            # Generate ISO timestamp
            interp_dt = datetime.fromtimestamp(interp_ts, tz=timezone.utc)
            interp_t_str = interp_dt.isoformat()
            
            result.append({"t": interp_t_str, "index": interp_val})
            step += 1
    
    # Add the last original point
    result.append({"t": points[-1][2], "index": points[-1][1]})
    
    return result
