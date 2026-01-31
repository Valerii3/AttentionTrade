import uuid
from datetime import datetime, timezone, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.src.constants import period_to_minutes
from backend.src.db import queries as db
from backend.src.services.trading import prices_from_position
from backend.src.services.index_pipeline import get_iso_now, build_index
from backend.src.services.tools import get_available_tools

router = APIRouter(prefix="/events", tags=["events"])

VALID_PERIODS = ("1h", "8h", "24h", "1w")


class ProposeEventBody(BaseModel):
    name: str
    period: Literal["1h", "8h", "24h", "1w"]
    sourceUrl: Optional[str] = None
    description: Optional[str] = None


class TradeBody(BaseModel):
    side: str  # "up" | "down"
    amount: float


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
    net_up, net_down = await db.get_position(e["id"])
    price_up, price_down = prices_from_position(net_up, net_down)
    return {
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


def _default_search(_query: str) -> str:
    """Default search: no results (plug in real API via env or service later)."""
    return ""


@router.post("")
async def propose_event(body: ProposeEventBody):
    """Propose an event: initial reasonability check (Google Search), then agent, index build, accept decision."""
    if not body.name or not body.name.strip():
        raise HTTPException(status_code=400, detail="name required")
    try:
        window_minutes = period_to_minutes(body.period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        from agent.propose_agent import initial_reasonability_check, select_tools_and_config, should_accept_event
    except Exception:
        from agent.propose_agent import select_tools_and_config, should_accept_event
        initial_reasonability_check = None

    reasonability = None
    if initial_reasonability_check is not None:
        try:
            reasonability = initial_reasonability_check(
                body.name.strip(),
                body.sourceUrl,
                body.description,
                search_fn=_default_search,
            )
        except Exception:
            reasonability = {"pass": True, "reason": "Check failed; proceeding."}
    if reasonability is not None and not reasonability.get("pass", True):
        event_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(minutes=window_minutes)
        config = {
            "channels": ["Hacker News", "Reddit"],
            "tools": ["hn_frontpage", "reddit"],
            "keywords": [body.name],
            "exclusions": [],
            "window_minutes": window_minutes,
            "source_url": body.sourceUrl,
            "description": body.description,
            "reject_reason": reasonability.get("reason", "Event did not pass initial reasonability check."),
        }
        await db.create_event(
            event_id=event_id,
            name=body.name.strip(),
            status="rejected",
            window_start=now.isoformat(),
            window_end=window_end.isoformat(),
            index_start=100.0,
            config=config,
        )
        await db.update_event_on_reject(event_id, config)
        event = await db.get_event(event_id)
        return await _event_to_response_async(event)

    available_tools = [{"id": t["id"], "name": t["name"], "description": t["description"]} for t in get_available_tools()]
    try:
        config = select_tools_and_config(
            body.name.strip(),
            body.sourceUrl,
            body.description,
            available_tools,
            window_minutes,
        )
    except Exception:
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
        name=body.name.strip(),
        status="proposed",
        window_start=window_start_str,
        window_end=window_end_str,
        index_start=100.0,
        config=config,
    )
    index_value, activity = await build_index(event_id, config)
    try:
        decision = should_accept_event(body.name.strip(), index_value, activity)
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
        await db.update_event_on_reject(event_id, config)
    event = await db.get_event(event_id)
    return await _event_to_response_async(event)


@router.get("")
async def list_events(status: Optional[str] = None):
    events = await db.list_events(status=status)
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
    await db.add_trade(event_id, body.side, body.amount)
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
