"""
Attention Markets API. Run from project root: uvicorn backend.src.main:app --reload
"""
import asyncio
import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # Load .env from cwd (project root when running uvicorn from project root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Project root on path so agent can be imported
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.src.db import queries as db
from backend.src.routes.events import router as events_router
from backend.src.routes.profile import router as profile_router
from backend.src.services.index_pipeline import compute_index, get_iso_now
from backend.src.services.trading import prices_from_position

# Per-event baseline activity cache for index delta (in-memory for hackathon)
_baseline_activity: dict[str, dict] = {}


async def tick_index():
    """Every 1 min (demo): update index for all open events."""
    while True:
        await asyncio.sleep(60)
        events = await db.list_events(status="open")
        for event in events:
            eid = event["id"]
            config = event.get("config") or {}
            prev = _baseline_activity.get(eid)
            index_val, activity = compute_index(config, prev, {})
            _baseline_activity[eid] = activity
            await db.update_event_index(eid, index_val)
            await db.add_index_snapshot(eid, get_iso_now(), index_val)


async def check_resolutions():
    """Every 30s: resolve events whose window_end has passed."""
    while True:
        await asyncio.sleep(30)
        events = await db.list_events(status="open")
        now = get_iso_now()
        for event in events:
            if event["window_end"] <= now:
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    task_index = asyncio.create_task(tick_index())
    task_resolve = asyncio.create_task(check_resolutions())
    yield
    task_index.cancel()
    task_resolve.cancel()
    try:
        await task_index
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
