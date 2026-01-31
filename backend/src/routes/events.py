import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.src.db import queries as db
from backend.src.services.trading import prices_from_position
from backend.src.services.index_pipeline import get_iso_now, build_index
from backend.src.services.tools import get_available_tools

router = APIRouter(prefix="/events", tags=["events"])
logger = logging.getLogger(__name__)


DEFAULT_WINDOW_MINUTES = 1440  # 24h

class ProposeEventBody(BaseModel):
    name: str
    windowMinutes: Optional[int] = None  # optional; default 24h
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
    }
    if e.get("status") == "rejected" and isinstance(e.get("config"), dict):
        out["rejectReason"] = e["config"].get("reject_reason") or "Event not accepted for trading."
    return out


@router.post("")
async def propose_event(body: ProposeEventBody):
    """Propose an event: initial reasonability check (Gemini + Google Search), then agent, index build, accept decision."""
    if not body.name or not body.name.strip():
        raise HTTPException(status_code=400, detail="name required")
    window_minutes = body.windowMinutes if body.windowMinutes is not None and body.windowMinutes >= 1 else DEFAULT_WINDOW_MINUTES

    logger.info("Propose event: name=%r, running reasonability check...", body.name.strip())

    try:
        from agent.propose_agent import (
            initial_reasonability_check,
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

    reasonability = None
    if initial_reasonability_check is not None:
        try:
            reasonability = initial_reasonability_check(body.name.strip(), body.sourceUrl, body.description)
            logger.info("Reasonability check: pass=%s, reason=%s", reasonability.get("pass"), reasonability.get("reason", ""))
        except Exception as exc:
            logger.warning("Reasonability check failed: %s", exc, exc_info=True)
            reasonability = {"pass": False, "reason": "Analysis failed; event rejected."}

    if reasonability is not None and not reasonability.get("pass", True):
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
            "source_url": body.sourceUrl,
            "description": body.description,
        }
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
        return {"suggestedWindowMinutes": max(1, int(suggested))}
    except Exception:
        return {"suggestedWindowMinutes": 60}


@router.get("")
async def list_events(status: Optional[str] = None):
    # Default to open so main page shows only tradeable events
    effective_status = status if status is not None else "open"
    events = await db.list_events(status=effective_status)
    out = []
    for e in events:
        out.append(await _event_to_response_async(e))
    return {"events": out}


@router.get("/{event_id}")
async def get_event(event_id: str):
    event = await db.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return await _event_to_response_async(event)


@router.get("/{event_id}/index-history")
async def get_index_history(event_id: str):
    event = await db.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    history = await db.get_index_history(event_id)
    return {"history": history}


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
