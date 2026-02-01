import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.src.constants import market_type_to_minutes
from backend.src.db import queries as db
from backend.src.services.trading import prices_from_position
from backend.src.services.index_pipeline import get_iso_now, build_index
from backend.src.services.tools import get_available_tools

router = APIRouter(prefix="/events", tags=["events"])
logger = logging.getLogger(__name__)

# Canonical default: 1h market
DEFAULT_MARKET_TYPE = "1h"

# Directory for generated event thumbnails (project root / event_images)
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
EVENT_IMAGES_DIR = os.environ.get("ATTENTION_EVENT_IMAGES", os.path.join(_project_root, "event_images"))


class ProposeEventBody(BaseModel):
    name: str
    marketType: Optional[str] = None  # "1h" | "24h"; default 1h
    windowMinutes: Optional[int] = None  # ignored for normal flow; used only for demo override
    demo: Optional[bool] = False  # if True: 2-min window, synthetic index, labeled demo
    sourceUrl: Optional[str] = None
    description: Optional[str] = None


class SuggestWindowBody(BaseModel):
    name: str
    sourceUrl: Optional[str] = None
    description: Optional[str] = None


class TradeBody(BaseModel):
    side: str  # "up" | "down"
    amount: float
    trader_id: Optional[str] = None


class CommentBody(BaseModel):
    text: str
    traderId: Optional[str] = None
    displayName: Optional[str] = None


def _event_to_response(e: dict) -> dict:
    net_up, net_down = 0.0, 0.0
    try:
        net_up, net_down = __import__("asyncio").get_event_loop().run_until_complete(db.get_position(e["id"]))
    except Exception:
        pass
    # We'll get position in the route with await
    return {
        "id": e["id"],
        "name": e["name"],
        "status": e["status"],
        "windowStart": e["window_start"],
        "windowEnd": e["window_end"],
        "indexStart": e["index_start"],
        "indexCurrent": e["index_current"],
        "resolution": e.get("resolution"),
        "priceUp": None,
        "priceDown": None,
        "createdAt": e["created_at"],
    }


async def _event_to_response_async(e: dict) -> dict:
    # Synthetic rejected events are not in DB; get_position returns 0,0 for unknown id
    net_up, net_down = await db.get_position(e["id"])
    price_up, price_down = prices_from_position(net_up, net_down)
    volume = await db.get_volume(e["id"])
    config = e.get("config") or {}
    out = {
        "id": e["id"],
        "name": e["name"],
        "status": e["status"],
        "windowStart": e["window_start"],
        "windowEnd": e["window_end"],
        "indexStart": e["index_start"],
        "indexCurrent": e["index_current"],
        "resolution": e.get("resolution"),
        "priceUp": price_up,
        "priceDown": price_down,
        "createdAt": e["created_at"],
        "marketType": config.get("market_type", DEFAULT_MARKET_TYPE),
        "demo": bool(config.get("demo")),
        "volume": round(volume, 2),
        "headline": config.get("headline"),
        "subline": config.get("subline"),
        "labelUp": config.get("label_up"),
        "labelDown": config.get("label_down"),
        "imageUrl": config.get("image_url") or config.get("thumbnail_url"),
    }
    if e.get("status") == "rejected" and isinstance(config, dict):
        out["rejectReason"] = config.get("reject_reason") or "Event not accepted for trading."
    return out


@router.post("")
async def propose_event(body: ProposeEventBody):
    """Propose an event: initial reasonability check (Gemini + Google Search), then agent, index build, accept decision."""
    if not body.name or not body.name.strip():
        raise HTTPException(status_code=400, detail="name required")
    market_type = (body.marketType or DEFAULT_MARKET_TYPE).strip().lower()
    if market_type not in ("1h", "24h"):
        market_type = DEFAULT_MARKET_TYPE
    window_minutes = market_type_to_minutes(market_type)
    # Demo override: 2-min window, synthetic index
    if body.demo:
        window_minutes = 2
    elif body.windowMinutes is not None and body.windowMinutes >= 1:
        window_minutes = body.windowMinutes

    logger.info("Propose event: name=%r, marketType=%s, demo=%s, running reasonability check...", body.name.strip(), market_type, bool(body.demo))

    try:
        from agent.propose_agent import (
            initial_reasonability_check,
            reject_reason_if_outcome_style,
            select_tools_and_config,
            should_accept_event,
            has_traction,
            NO_ATTENTION_REASON,
        )
    except Exception:
        from agent.propose_agent import (
            select_tools_and_config,
            should_accept_event,
            has_traction,
            NO_ATTENTION_REASON,
        )
        initial_reasonability_check = None
        reject_reason_if_outcome_style = None

    # Demo: skip outcome-style and reasonability checks so any topic works
    if not body.demo:
        # Reject outcome-style markets (resolvable by one number) in favor of attention-native framing
        if reject_reason_if_outcome_style is not None:
            outcome_reason = reject_reason_if_outcome_style(body.name.strip(), body.description)
            if outcome_reason:
                logger.info("Event rejected (outcome-style): %s", outcome_reason)
                now = datetime.now(timezone.utc)
                window_end = now + timedelta(minutes=window_minutes)
                synthetic = {
                    "id": str(uuid.uuid4()),
                    "name": body.name.strip(),
                    "status": "rejected",
                    "window_start": now.isoformat(),
                    "window_end": window_end.isoformat(),
                    "index_start": 100.0,
                    "index_current": 100.0,
                    "resolution": None,
                    "config": {"reject_reason": outcome_reason},
                    "created_at": now.isoformat(),
                }
                return await _event_to_response_async(synthetic)

    reasonability = None
    if not body.demo and initial_reasonability_check is not None:
        try:
            reasonability = initial_reasonability_check(body.name.strip(), body.sourceUrl, body.description)
            logger.info("Reasonability check: pass=%s, reason=%s", reasonability.get("pass"), reasonability.get("reason", ""))
        except Exception as exc:
            logger.warning("Reasonability check failed: %s", exc, exc_info=True)
            reasonability = {"pass": False, "reason": "Analysis failed; event rejected."}

    if not body.demo and reasonability is not None and not reasonability.get("pass", True):
        logger.info("Event rejected after reasonability check: %s", reasonability.get("reason"))
        # Do not persist rejected events; return synthetic response so frontend can show rejectReason
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(minutes=window_minutes)
        synthetic = {
            "id": str(uuid.uuid4()),
            "name": body.name.strip(),
            "status": "rejected",
            "window_start": now.isoformat(),
            "window_end": window_end.isoformat(),
            "index_start": 100.0,
            "index_current": 100.0,
            "resolution": None,
            "config": {"reject_reason": reasonability.get("reason", "Event did not pass initial reasonability check.")},
            "created_at": now.isoformat(),
        }
        return await _event_to_response_async(synthetic)

    if body.demo:
        config = {
            "channels": ["Hacker News", "Reddit"],
            "tools": ["hn_frontpage", "reddit"],
            "keywords": [body.name],
            "exclusions": [],
            "window_minutes": 2,
            "market_type": market_type,
            "demo": True,
            "demo_window_minutes": 2,
            "source_url": body.sourceUrl,
            "description": body.description,
        }
    else:
        available_tools = [{"id": t["id"], "name": t["name"], "description": t["description"]} for t in get_available_tools()]
        try:
            from agent.propose_agent import select_tools_and_config, should_accept_event
            config = select_tools_and_config(
                body.name,
                body.sourceUrl,
                body.description,
                available_tools,
                window_minutes,
            )
        except Exception:
            from agent.propose_agent import should_accept_event
            config = {
                "channels": ["Hacker News", "Reddit"],
                "tools": ["hn_frontpage", "reddit"],
                "keywords": [body.name],
                "exclusions": [],
                "window_minutes": window_minutes,
                "market_type": market_type,
                "source_url": body.sourceUrl,
                "description": body.description,
            }
        config["market_type"] = config.get("market_type") or market_type

    # AI-generated headline/subline and button labels (emotional hook + conceptual clarity)
    try:
        from agent.propose_agent import suggest_headline_subline
        hl = suggest_headline_subline(
            body.name.strip(),
            market_type,
            source_url=body.sourceUrl,
            description=body.description,
        )
        config["headline"] = hl.get("headline")
        config["subline"] = hl.get("subline")
        config["label_up"] = hl.get("label_up", "Heating up")
        config["label_down"] = hl.get("label_down", "Cooling down")
    except Exception:
        config["headline"] = f"Is {body.name.strip()} gaining momentum?" if market_type == "1h" else f"Will {body.name.strip()} stay hot?"
        config["subline"] = "Attention change · next 60 min" if market_type == "1h" else "Sustained attention · next 24h"
        config["label_up"] = "Heating up"
        config["label_down"] = "Cooling down"

    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(minutes=window_minutes)
    window_start_str = now.isoformat()
    window_end_str = window_end.isoformat()
    await db.create_event(
        event_id=event_id,
        name=body.name,
        status="proposed",
        window_start=window_start_str,
        window_end=window_end_str,
        index_start=100.0,
        config=config,
    )

    def _maybe_generate_image():
        try:
            from agent.propose_agent import generate_event_image
            headline = config.get("headline") or body.name
            path = generate_event_image(body.name, headline, event_id, EVENT_IMAGES_DIR)
            if path:
                config["image_url"] = "/api/events/" + event_id + "/image"
        except Exception as e:
            logger.warning("Event image generation skipped: %s", e)

    if body.demo:
        # Demo: skip real index build and traction; accept immediately; tick_demo_index will drive synthetic index
        _maybe_generate_image()
        await db.add_index_snapshot(event_id, get_iso_now(), 100.0)
        await db.update_event_on_accept(
            event_id,
            window_start_str,
            window_end_str,
            100.0,
            100.0,
            config,
        )
    else:
        index_value, activity = await build_index(event_id, config)

        if not has_traction(activity):
            config["reject_reason"] = NO_ATTENTION_REASON
            await db.update_event_on_reject(event_id, config)
            event = await db.get_event(event_id)
            return await _event_to_response_async(event)

        try:
            decision = should_accept_event(body.name, index_value, activity)
            accepted = decision.get("accept", True)
        except Exception:
            accepted = True
        if accepted:
            _maybe_generate_image()
            await db.update_event_on_accept(
                event_id,
                window_start_str,
                window_end_str,
                100.0,
                index_value,
                config,
            )
        else:
            config["reject_reason"] = decision.get("reason", "Event not accepted for trading.")
            await db.update_event_on_reject(event_id, config)
    event = await db.get_event(event_id)
    return await _event_to_response_async(event)


@router.post("/suggest-window")
async def suggest_window(body: SuggestWindowBody):
    """Return AI-suggested window duration in minutes for the given event name/URL/description."""
    if not body.name or not body.name.strip():
        raise HTTPException(status_code=400, detail="name required")
    available_tools = [{"id": t["id"], "name": t["name"], "description": t["description"]} for t in get_available_tools()]
    try:
        from agent.event_definition import event_definition
        config = event_definition(
            body.name.strip(),
            0,
            source_url=body.sourceUrl,
            description=body.description,
            available_tools=available_tools,
            suggest_window_only=True,
        )
        suggested = config.get("suggested_window_minutes", 60)
        # Return only canonical windows: 60 or 1440
        mins = max(1, int(suggested))
        if mins >= 1440:
            mins = 1440
        else:
            mins = 60
        return {"suggestedWindowMinutes": mins}
    except Exception:
        return {"suggestedWindowMinutes": 60}


@router.get("")
async def list_events(
    status: Optional[str] = None,
    name: Optional[str] = None,
    q: Optional[str] = None,
):
    # Default to open so main page shows only tradeable events
    effective_status = status if status is not None else "open"
    topic_name = name.strip() if name else None
    search_q = q.strip() if q else None
    events = await db.list_events(
        status=effective_status,
        name=topic_name,
        q=search_q,
    )
    out = []
    for e in events:
        out.append(await _event_to_response_async(e))
    return {"events": out}


@router.get("/{event_id}/index-history")
async def get_index_history(event_id: str):
    event = await db.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    history = await db.get_index_history(event_id)
    return {"history": history}


def _comment_to_response(c: dict) -> dict:
    return {
        "id": c["id"],
        "eventId": c["event_id"],
        "traderId": c.get("trader_id"),
        "displayName": c.get("display_name"),
        "body": c["body"],
        "createdAt": c["created_at"],
    }


@router.get("/{event_id}/comments")
async def get_event_comments(event_id: str):
    event = await db.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    comments = await db.list_comments(event_id)
    return {"comments": [_comment_to_response(c) for c in comments]}


@router.post("/{event_id}/comments")
async def post_comment(event_id: str, body: CommentBody):
    if not body.text or not body.text.strip():
        raise HTTPException(status_code=400, detail="text required")
    event = await db.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event["status"] not in ("open", "resolved"):
        raise HTTPException(status_code=409, detail="Comments not allowed for this event")
    comment = await db.add_comment(
        event_id,
        body.text.strip(),
        trader_id=body.traderId,
        display_name=body.displayName,
    )
    return _comment_to_response(comment)


@router.post("/{event_id}/trade")
async def trade(event_id: str, body: TradeBody):
    if body.side not in ("up", "down"):
        raise HTTPException(status_code=400, detail="side must be 'up' or 'down'")
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be positive")
    event = await db.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event["status"] != "open":
        raise HTTPException(status_code=409, detail="Event is not open for trading")
    await db.add_trade(event_id, body.side, body.amount, body.trader_id)
    net_up, net_down = await db.get_position(event_id)
    price_up, price_down = prices_from_position(net_up, net_down)
    return {"ok": True, "priceUp": price_up, "priceDown": price_down}


@router.get("/{event_id}/explanation")
async def get_explanation(event_id: str):
    event = await db.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    explanation = event.get("explanation") or ""
    if not explanation:
        return {"explanation": None}
    return {"explanation": explanation}


@router.get("/{event_id}/image")
async def get_event_image(event_id: str):
    """Serve the generated thumbnail image for the event, if it exists."""
    path = os.path.join(EVENT_IMAGES_DIR, f"{event_id}.png")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path, media_type="image/png")


@router.get("/{event_id}")
async def get_event(event_id: str):
    event = await db.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return await _event_to_response_async(event)
