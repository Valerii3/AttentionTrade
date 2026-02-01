"""
Attention Markets API. Run from project root: uvicorn backend.src.main:app --reload
"""
import asyncio
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

load_dotenv()  # Load .env from cwd (project root when running uvicorn from project root)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Project root on path so agent can be imported
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.src.db import queries as db
from backend.src.routes.events import router as events_router
from backend.src.routes.profile import router as profile_router
from backend.src.services.index_pipeline import compute_index, get_iso_now, build_index, parse_iso_utc
from backend.src.services.trading import prices_from_position
from backend.src.services.demo_index import compute_demo_index

# Per-event baseline activity cache for index delta (in-memory for hackathon)
_baseline_activity: dict[str, dict] = {}


async def tick_index():
    """Every 1 min: update index for all open non-demo events."""
    while True:
        await asyncio.sleep(60)
        events = await db.list_events(status="open")
        now = get_iso_now()
        for event in events:
            config = event.get("config") or {}
            if config.get("demo"):
                continue
            eid = event["id"]
            prev = _baseline_activity.get(eid)
            index_val, activity = compute_index(config, prev, {})
            _baseline_activity[eid] = activity
            await db.update_event_index(eid, index_val)
            await db.add_index_snapshot(eid, now, index_val)


async def tick_demo_index():
    """Every 5 min: update synthetic index for open demo events only."""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        events = await db.list_events(status="open")
        now = get_iso_now()
        for event in events:
            config = event.get("config") or {}
            if not config.get("demo"):
                continue
            eid = event["id"]
            index_val = compute_demo_index(eid, event["window_start"], now)
            await db.update_event_index(eid, index_val)
            await db.add_index_snapshot(eid, now, index_val)


async def open_next_window(resolved_event: dict) -> None:
    """After resolution, open a new window for the same topic (recurring market). Skip demo events."""
    config = resolved_event.get("config") or {}
    if config.get("demo"):
        return
    window_minutes = config.get("window_minutes", 60)
    # Clamp to canonical 60 or 1440 for recurring
    if window_minutes >= 1440:
        window_minutes = 1440
    else:
        window_minutes = 60
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(minutes=window_minutes)
    now_str = now.isoformat()
    window_end_str = window_end.isoformat()
    new_id = str(uuid.uuid4())
    await db.create_event(
        event_id=new_id,
        name=resolved_event["name"],
        status="open",
        window_start=now_str,
        window_end=window_end_str,
        index_start=100.0,
        config=config,
    )
    _, activity = await build_index(new_id, config)
    _baseline_activity[new_id] = activity


def _window_end_passed(event: dict, now_iso: str) -> bool:
    """True if event's window_end is at or before now (robust datetime comparison)."""
    try:
        window_end_dt = parse_iso_utc(event["window_end"])
        now_dt = parse_iso_utc(now_iso)
        return window_end_dt <= now_dt
    except (ValueError, TypeError):
        return False


async def _resolve_one_event(event: dict) -> None:
    """Resolve one event and open next window (recurring)."""
    index_start = event["index_start"]
    index_current = event["index_current"]
    resolution = "up" if index_current > index_start else "down"
    snapshots = await db.get_index_history(event["id"])
    try:
        from agent.explanations import explain_index_movement
        explanation = explain_index_movement(
            event["name"], index_start, index_current, snapshots
        )
    except Exception:
        explanation = f"Attention {'rose' if resolution == 'up' else 'fell'} (index {index_start} -> {index_current})."
    await db.resolve_event(event["id"], resolution, explanation)
    await open_next_window(event)


async def run_resolution_catch_up() -> None:
    """On startup: resolve any open events whose window_end has already passed."""
    events = await db.list_events(status="open")
    now = get_iso_now()
    for event in events:
        if _window_end_passed(event, now):
            await _resolve_one_event(event)


async def check_resolutions():
    """Every 30s: resolve events whose window_end has passed, then open next window (recurring)."""
    while True:
        await asyncio.sleep(30)
        events = await db.list_events(status="open")
        now = get_iso_now()
        for event in events:
            if _window_end_passed(event, now):
                await _resolve_one_event(event)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    await run_resolution_catch_up()
    task_index = asyncio.create_task(tick_index())
    task_demo = asyncio.create_task(tick_demo_index())
    task_resolve = asyncio.create_task(check_resolutions())
    yield
    task_index.cancel()
    task_demo.cancel()
    task_resolve.cancel()
    try:
        await task_index
        await task_demo
        await task_resolve
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Attention Markets API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(events_router)
app.include_router(profile_router)


@app.post("/events/{event_id}/resolve")
async def resolve_event_now(event_id: str):
    """Force resolution for an open event whose window_end has passed (dev/manual catch-up)."""
    event = await db.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event["status"] != "open":
        raise HTTPException(status_code=400, detail="Event is not open for resolution")
    now = get_iso_now()
    if not _window_end_passed(event, now):
        raise HTTPException(status_code=400, detail="Event window has not ended yet")
    await _resolve_one_event(event)
    return {"ok": True}
