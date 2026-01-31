from fastapi import APIRouter, HTTPException

from backend.src.db import queries as db

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/trades")
async def get_profile_trades(trader_id: str):
    """Return all trades for a trader with event name, status, resolution."""
    if not trader_id or not trader_id.strip():
        raise HTTPException(status_code=400, detail="trader_id required")
    rows = await db.list_trades_by_trader(trader_id.strip())
    trades = [
        {
            "eventId": r["event_id"],
            "eventName": r["event_name"],
            "side": r["side"],
            "amount": r["amount"],
            "createdAt": r["created_at"],
            "status": r["event_status"],
            "resolution": r["resolution"],
        }
        for r in rows
    ]
    return {"trades": trades}
