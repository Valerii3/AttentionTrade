from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.src.db import queries as db

router = APIRouter(prefix="/profile", tags=["profile"])


class UpdateProfileBody(BaseModel):
    displayName: Optional[str] = None


# Note: /trades must come before /{trader_id} to avoid path conflicts
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
            "executionPrice": r.get("execution_price"),
        }
        for r in rows
    ]
    return {"trades": trades}


@router.get("/{trader_id}")
async def get_profile(trader_id: str):
    """Return profile including balance. Creates profile with balance=100 if new."""
    if not trader_id or not trader_id.strip():
        raise HTTPException(status_code=400, detail="trader_id required")
    profile = await db.get_or_create_profile(trader_id.strip())
    return {
        "traderId": profile["trader_id"],
        "displayName": profile["display_name"],
        "balance": profile["balance"],
        "createdAt": profile["created_at"],
    }


@router.patch("/{trader_id}")
async def update_profile(trader_id: str, body: UpdateProfileBody):
    """Update profile display name."""
    if not trader_id or not trader_id.strip():
        raise HTTPException(status_code=400, detail="trader_id required")
    # Ensure profile exists
    await db.get_or_create_profile(trader_id.strip())
    if body.displayName is not None:
        await db.update_profile_display_name(trader_id.strip(), body.displayName)
    profile = await db.get_or_create_profile(trader_id.strip())
    return {
        "traderId": profile["trader_id"],
        "displayName": profile["display_name"],
        "balance": profile["balance"],
        "createdAt": profile["created_at"],
    }
