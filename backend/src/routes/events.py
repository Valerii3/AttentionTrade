import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.src.db import queries as db
from backend.src.services.trading import prices_from_position
from backend.src.services.index_pipeline import compute_index, get_iso_now

router = APIRouter(prefix="/events", tags=["events"])


class CreateEventBody(BaseModel):
    name: str
    windowMinutes: int


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


@router.post("")
async def create_event(body: CreateEventBody):
    if not body.name or body.windowMinutes < 1:
        raise HTTPException(status_code=400, detail="name and windowMinutes required")
    try:
        from agent.event_definition import event_definition
        config = event_definition(body.name, body.windowMinutes)
    except Exception:
        config = {
            "channels": ["Hacker News", "Reddit"],
            "keywords": [body.name],
            "exclusions": [],
            "window_minutes": body.windowMinutes,
        }
    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(minutes=body.windowMinutes)
    window_start_str = now.isoformat()
    window_end_str = window_end.isoformat()
    await db.create_event(
        event_id=event_id,
        name=body.name,
        status="open",
        window_start=window_start_str,
        window_end=window_end_str,
        index_start=100.0,
        config=config,
    )
    # Insert initial snapshot
    await db.add_index_snapshot(event_id, get_iso_now(), 100.0)
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
