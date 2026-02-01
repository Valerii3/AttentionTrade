"""
6-month attention index: Part A = faked Deep Research (synthetic series, not wired).
Part B = Gemini + Google Search to build monthly index and backfill chart.
"""
import hashlib
import json
import logging
import math
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)

# --- Part A: Attention types and traction rules (not wired in flow) ---

ATTENTION_TYPES = ("startup", "product", "person", "event", "narrative", "default")

# Traction rules per type: what drives attention (for synthetic curve shape).
TRACTION_RULES: dict[str, list[str]] = {
    "startup": ["virality", "github_stars", "hn_reddit_buzz"],
    "product": ["reviews", "mentions", "search_trend"],
    "person": ["social_following", "media_mentions"],
    "event": ["coverage", "search_trend"],
    "narrative": ["meme_spread", "citations"],
    "default": ["generic_attention"],
}


def _classify_attention_type(name: str, description: Optional[str]) -> str:
    """Heuristic classification from name + description. Not called from events.py."""
    text = f"{name} {description or ''}".lower()
    if re.search(r"\b(startup|funding|launch|vc|series [a-z]|y combinator)\b", text):
        return "startup"
    if re.search(r"\b(product|release|review|app|software|saas)\b", text):
        return "product"
    if re.search(r"\b(ceo|founder|influencer|politician|person)\b", text):
        return "person"
    if re.search(r"\b(event|conference|summit|election|game)\b", text):
        return "event"
    if re.search(r"\b(narrative|meme|trend|story|discourse)\b", text):
        return "narrative"
    return "default"


def _seed_from_event_id(event_id: str) -> int:
    """Deterministic seed from event_id."""
    h = hashlib.sha256(event_id.encode()).hexdigest()
    return int(h[:8], 16)


def _parse_iso(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def generate_synthetic_6mo_series(
    event_id: str,
    name: str,
    config: dict,
    current_index_value: float,
    now_iso: str,
) -> list[tuple[str, float]]:
    """
    Part A only. Generate deterministic 6-month series: baseline 100 at start,
    ending near current_index_value. Shape varies by attention type. Not called from events.py.
    Returns list of (t_iso, value); all t < now.
    """
    try:
        now = _parse_iso(now_iso)
    except (ValueError, TypeError):
        return []
    seed = _seed_from_event_id(event_id)
    attn_type = _classify_attention_type(name, config.get("description") or "")
    # Existence start: some topics "start" later (hash to month offset 0..4)
    months_back = 6 - (seed % 3)  # 4, 5, or 6 months
    start = now - timedelta(days=months_back * 30)
    points: list[tuple[str, float]] = []
    # One point per month
    for i in range(months_back + 1):
        t = start + timedelta(days=i * 30)
        if t >= now:
            break
        t_iso = t.isoformat()
        # Progress 0..1 over the period
        progress = i / max(months_back, 1)
        # Shape by type: startup = volatile, narrative = S-curve, etc.
        if attn_type == "startup":
            wave = 8 * math.sin(progress * math.pi * 2 + seed % 10)
            base = 100 + progress * (current_index_value - 100) * 0.7
            value = base + wave
        elif attn_type == "narrative":
            # S-curve
            s = 1 / (1 + math.exp(-8 * (progress - 0.5)))
            value = 100 + s * (current_index_value - 100) * 0.9
        elif attn_type == "event":
            # Spike in middle
            spike = 15 * math.exp(-((progress - 0.5) ** 2) * 20)
            value = 100 + progress * (current_index_value - 100) * 0.5 + spike
        else:
            # Linear trend + small noise
            noise = ((seed + i * 31) % 100) / 100.0 * 4 - 2
            value = 100 + progress * (current_index_value - 100) + noise
        value = max(70.0, min(130.0, value))
        points.append((t_iso, round(value, 2)))
    return points


async def backfill_research_index_fake(
    event_id: str,
    name: str,
    config: dict,
    current_index_value: float,
) -> None:
    """
    Part A only. Insert synthetic 6-month series into index_snapshots (historical only).
    Not called from events.py; available as fallback or for future Deep Research.
    """
    from backend.src.db import queries as db

    now_iso = datetime.now(timezone.utc).isoformat()
    points = generate_synthetic_6mo_series(event_id, name, config, current_index_value, now_iso)
    if not points:
        return
    await db.add_index_snapshots_batch(event_id, points)
    logger.info("Backfilled %d synthetic 6mo points for event %s (fake research)", len(points), event_id)


# --- Part B: Gemini + Google Search monthly index (actual path) ---


def _parse_json_from_text(text: str) -> Optional[Any]:
    """Extract first JSON object or array from text. Handles markdown fences."""
    text = text.strip()
    if not text:
        return None
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0].strip()
    # Try full parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find first { or [
    start_obj = text.find("{")
    start_arr = text.find("[")
    start = -1
    end_char = ""
    if start_obj >= 0 and (start_arr < 0 or start_obj < start_arr):
        start = start_obj
        end_char = "}"
    elif start_arr >= 0:
        start = start_arr
        end_char = "]"
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] in "{[":
            depth += 1
        elif text[i] in "}]":
            depth -= 1
            if depth == 0 and text[i] == end_char:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _month_to_iso(month_str: str) -> Optional[str]:
    """Convert 'YYYY-MM' to ISO timestamp (first day of month, UTC)."""
    try:
        parts = month_str.strip().split("-")
        if len(parts) >= 2:
            y, m = int(parts[0]), int(parts[1])
            if 1 <= m <= 12:
                dt = datetime(y, m, 1, tzinfo=timezone.utc)
                return dt.isoformat()
    except (ValueError, TypeError):
        pass
    return None


def build_monthly_attention_index_via_gemini(
    name: str,
    source_url: Optional[str],
    description: Optional[str],
    current_index_value: float,
) -> list[tuple[str, float]]:
    """
    Call Gemini with Google Search to get a monthly attention index for the topic
    (last 6 months, baseline 100). Returns list of (t_iso, value); empty on failure.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return []

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
    except ImportError:
        return []

    user_parts = [f"Topic/event name: {name}."]
    if source_url:
        user_parts.append(f"Source URL: {source_url}")
    if description:
        user_parts.append(f"Description: {description}")
    user_content = " ".join(user_parts)

    prompt = (
        "You build a monthly ATTENTION INDEX for this topic over the last 6 months (or as far back as the topic has existed). "
        "Use Google Search to infer from news, social media, and trends whether attention to this topic went UP or DOWN each month. "
        "Index starts at 100 for the first month; later months are relative (e.g. 105 = more attention, 95 = less). "
        "Include each month as YYYY-MM. If the topic did not exist 6 months ago, start from the month it became relevant. "
        "Reply with ONLY a JSON object with a single key 'points' which is an array of objects, each with 'month' (string YYYY-MM) and 'index' (number). "
        "Example: {\"points\": [{\"month\": \"2024-08\", \"index\": 100}, {\"month\": \"2024-09\", \"index\": 105}]}. "
        "No markdown, no code fences.\n\n"
        + user_content
    )

    try:
        grounding_tool = genai.types.Tool(google_search=genai.types.GoogleSearch())
        config = genai.types.GenerateContentConfig(tools=[grounding_tool])
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=config,
        )
        text = getattr(response, "text", None) or (
            response.candidates[0].content.parts[0].text
            if response.candidates and response.candidates[0].content.parts
            else None
        )
        if not text:
            return []
        text = (text or "").strip()
        out = _parse_json_from_text(text)
        if not out:
            return []

        # Accept {"points": [...]} or direct [...]
        raw_points = out.get("points") if isinstance(out, dict) else out
        if not isinstance(raw_points, list):
            return []

        now = datetime.now(timezone.utc)
        points: list[tuple[str, float]] = []
        for i, item in enumerate(raw_points):
            if not isinstance(item, dict):
                continue
            month = item.get("month")
            idx_val = item.get("index")
            if month is None or idx_val is None:
                continue
            t_iso = _month_to_iso(str(month))
            if not t_iso:
                continue
            try:
                val = float(idx_val)
            except (TypeError, ValueError):
                continue
            # Only include past months (t < now) so we don't duplicate build_index snapshot
            try:
                ts = _parse_iso(t_iso)
                if ts >= now:
                    # Replace current month with current_index_value and still add it as "last historical"
                    val = current_index_value
                    points.append((t_iso, round(val, 2)))
                    break
            except (ValueError, TypeError):
                pass
            points.append((t_iso, round(val, 2)))

        # If last point is current month, align to current_index_value
        if points:
            last_t = points[-1][0]
            try:
                last_dt = _parse_iso(last_t)
                if last_dt.year == now.year and last_dt.month == now.month:
                    points[-1] = (last_t, round(current_index_value, 2))
            except (ValueError, TypeError):
                pass

        return points
    except Exception as e:
        logger.warning("Gemini monthly index failed: %s", e)
        return []


async def backfill_monthly_index(
    event_id: str,
    points: list[tuple[str, float]],
    now_iso: str,
) -> None:
    """Insert historical points (t < now_iso) into index_snapshots. Skips duplicate of 'now'."""
    from backend.src.db import queries as db

    to_insert: list[tuple[str, float]] = []
    for t_iso, value in points:
        if t_iso < now_iso:
            to_insert.append((t_iso, value))
    if not to_insert:
        return
    await db.add_index_snapshots_batch(event_id, to_insert)
    logger.info("Backfilled %d monthly index points for event %s", len(to_insert), event_id)


async def backfill_6mo_index_via_gemini(
    event_id: str,
    name: str,
    source_url: Optional[str],
    description: Optional[str],
    current_index_value: float,
) -> None:
    """
    Build 6-month attention index via Gemini + Google Search and backfill.
    On failure, optionally fall back to faked synthetic series.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    points = build_monthly_attention_index_via_gemini(
        name, source_url, description, current_index_value
    )
    if points:
        await backfill_monthly_index(event_id, points, now_iso)
    else:
        # Fallback: use faked synthetic series so chart still has 6mo data
        await backfill_research_index_fake(event_id, name, {"description": description}, current_index_value)


async def build_index_via_gemini(
    event_id: str,
    name: str,
    source_url: Optional[str],
    description: Optional[str],
) -> tuple[float, dict[str, float]]:
    """
    Build attention index via a single Gemini + Google Search call (no channel APIs).
    Rates the topic over up to 6 months (max); months with no traction use index 0.
    Persists one snapshot (now, current_index) and backfills historical points.
    Returns (current_index, activity) for use in accept decision.
    On failure: returns (100.0, {}) and optionally runs synthetic fallback for chart.
    """
    from backend.src.db import queries as db
    from backend.src.services.index_pipeline import get_iso_now

    now_iso = get_iso_now()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("build_index_via_gemini: no GEMINI_API_KEY; using default index 100")
        await db.add_index_snapshot(event_id, now_iso, 100.0)
        await db.update_event_index(event_id, 100.0)
        await backfill_research_index_fake(event_id, name, {"description": description}, 100.0)
        return 100.0, {}

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
    except ImportError:
        logger.warning("build_index_via_gemini: genai not available; using default index 100")
        await db.add_index_snapshot(event_id, now_iso, 100.0)
        await db.update_event_index(event_id, 100.0)
        await backfill_research_index_fake(event_id, name, {"description": description}, 100.0)
        return 100.0, {}

    user_parts = [f"Topic/event name: {name}."]
    if source_url:
        user_parts.append(f"Source URL: {source_url}")
    if description:
        user_parts.append(f"Description: {description}")
    user_content = " ".join(user_parts)

    prompt = (
        "Rate attention for this topic over the last up to 6 months (max 6 months) based on news, social media virality, etc. "
        "6 months is the maximum lookback. If the topic is newer and had no traction in month -6 or -5 (etc.), use index 0 for those months. "
        "Return JSON: current_index (number for today) and points (array of objects with month (string YYYY-MM) and index (number) for each month in the window; use 0 for months with no traction or before the topic existed). "
        "Example: {\"current_index\": 105, \"points\": [{\"month\": \"2024-08\", \"index\": 0}, {\"month\": \"2024-09\", \"index\": 95}]}. "
        "No markdown, no code fences.\n\n"
        + user_content
    )

    try:
        grounding_tool = genai.types.Tool(google_search=genai.types.GoogleSearch())
        genai_config = genai.types.GenerateContentConfig(tools=[grounding_tool])
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=genai_config,
        )
        text = getattr(response, "text", None) or (
            response.candidates[0].content.parts[0].text
            if response.candidates and response.candidates[0].content.parts
            else None
        )
        if not text:
            logger.warning("build_index_via_gemini: no response text; using default index 100")
            await db.add_index_snapshot(event_id, now_iso, 100.0)
            await db.update_event_index(event_id, 100.0)
            await backfill_research_index_fake(event_id, name, {"description": description}, 100.0)
            return 100.0, {}

        text = (text or "").strip()
        out = _parse_json_from_text(text)
        if not out or not isinstance(out, dict):
            logger.warning("build_index_via_gemini: invalid JSON; using default index 100")
            await db.add_index_snapshot(event_id, now_iso, 100.0)
            await db.update_event_index(event_id, 100.0)
            await backfill_research_index_fake(event_id, name, {"description": description}, 100.0)
            return 100.0, {}

        try:
            current_index = float(out.get("current_index", 100.0))
        except (TypeError, ValueError):
            current_index = 100.0
        current_index = max(0.0, min(200.0, current_index))  # clamp

        raw_points = out.get("points")
        if not isinstance(raw_points, list):
            raw_points = []

        now = datetime.now(timezone.utc)
        points: list[tuple[str, float]] = []
        for item in raw_points:
            if not isinstance(item, dict):
                continue
            month = item.get("month")
            idx_val = item.get("index")
            if month is None or idx_val is None:
                continue
            t_iso = _month_to_iso(str(month))
            if not t_iso:
                continue
            try:
                val = float(idx_val)
            except (TypeError, ValueError):
                continue
            val = max(0.0, min(200.0, val))
            try:
                ts = _parse_iso(t_iso)
                if ts >= now:
                    continue
            except (ValueError, TypeError):
                pass
            points.append((t_iso, round(val, 2)))

        await db.add_index_snapshot(event_id, now_iso, round(current_index, 2))
        await db.update_event_index(event_id, round(current_index, 2))
        if points:
            await backfill_monthly_index(event_id, points, now_iso)
        else:
            await backfill_research_index_fake(event_id, name, {"description": description}, current_index)

        activity = {"Gemini (6mo)": round(current_index, 2)}
        return round(current_index, 2), activity

    except Exception as e:
        logger.warning("build_index_via_gemini failed: %s", e, exc_info=True)
        await db.add_index_snapshot(event_id, now_iso, 100.0)
        await db.update_event_index(event_id, 100.0)
        await backfill_research_index_fake(event_id, name, {"description": description}, 100.0)
        return 100.0, {}
