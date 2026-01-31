"""
Synthetic Attention Index for demo markets. Mean-reverting with momentum bursts.
Deterministic given (event_id, window_start, now). Used only when config.demo is True.
Trading does not affect this index.
"""
import hashlib
import math
from datetime import datetime, timezone
from typing import Optional


def _parse_iso(s: str) -> datetime:
    """Parse ISO8601 to datetime (timezone-aware)."""
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _seed_from_event_id(event_id: str) -> int:
    """Deterministic seed from event_id for reproducible dynamics."""
    h = hashlib.sha256(event_id.encode()).hexdigest()
    return int(h[:8], 16)


def compute_demo_index(
    event_id: str,
    window_start_iso: str,
    now_iso: str,
) -> float:
    """
    Compute synthetic index for a demo event. Mean-reverting with momentum bursts.
    Index stays around 100 with waves (momentum) and small noise; bounded roughly 85–115.
    Deterministic for the same (event_id, window_start, now).
    """
    try:
        start = _parse_iso(window_start_iso)
        now = _parse_iso(now_iso) if isinstance(now_iso, str) else now_iso
    except (ValueError, TypeError):
        return 100.0
    elapsed_sec = (now - start).total_seconds()
    if elapsed_sec < 0:
        return 100.0
    seed = _seed_from_event_id(event_id)
    # Two wave components (momentum phases) + seeded "noise" for variety
    t = elapsed_sec / 30.0  # scale so ~1–2 min gives several cycles
    wave1 = 6.0 * math.sin(t * 1.2)
    wave2 = 4.0 * math.sin(t * 0.5 + (seed % 100) / 50.0)
    # Pseudo-noise from seed and t (deterministic)
    noise = ((seed * 17 + int(t) * 31) % 100) / 100.0 * 4.0 - 2.0
    delta = wave1 + wave2 + noise
    delta = max(-15.0, min(15.0, delta))
    return round(100.0 + delta, 2)
