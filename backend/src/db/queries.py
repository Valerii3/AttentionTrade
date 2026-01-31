import aiosqlite
import json
import os
from typing import Optional

# SQLite: single file, no server. Default path in project root when running uvicorn from project root.
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DB_PATH = os.environ.get("ATTENTION_DB_PATH", os.path.join(_root, "attention.db"))
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


async def get_db():
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db():
    with open(SCHEMA_PATH) as f:
        schema = f.read()
    conn = await get_db()
    try:
        await conn.executescript(schema)
        await conn.commit()
    finally:
        await conn.close()


async def create_event(
    event_id: str,
    name: str,
    status: str,
    window_start: str,
    window_end: str,
    index_start: float,
    config: dict,
) -> None:
    conn = await get_db()
    try:
        await conn.execute(
            """
            INSERT INTO events (id, name, status, window_start, window_end, index_start, index_current, config)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, name, status, window_start, window_end, index_start, index_start, json.dumps(config)),
        )
        await conn.execute(
            "INSERT INTO event_positions (event_id, net_up, net_down) VALUES (?, 0, 0)",
            (event_id,),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_event(event_id: str) -> Optional[dict]:
    conn = await get_db()
    try:
        cursor = await conn.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        )
        row = await cursor.fetchone()
    finally:
        await conn.close()
    if not row:
        return None
    r = dict(row)
    if r.get("config"):
        r["config"] = json.loads(r["config"])
    return r


async def list_events(status: Optional[str] = None) -> list[dict]:
    conn = await get_db()
    try:
        if status:
            cursor = await conn.execute(
                "SELECT * FROM events WHERE status = ? ORDER BY created_at DESC",
                (status,),
            )
        else:
            cursor = await conn.execute(
                "SELECT * FROM events ORDER BY created_at DESC"
            )
        rows = await cursor.fetchall()
    finally:
        await conn.close()
    out = []
    for row in rows:
        r = dict(row)
        if r.get("config"):
            r["config"] = json.loads(r["config"])
        out.append(r)
    return out


async def update_event_index(event_id: str, index_current: float) -> None:
    conn = await get_db()
    try:
        await conn.execute(
            "UPDATE events SET index_current = ? WHERE id = ?",
            (index_current, event_id),
        )
        await conn.commit()
    finally:
        await conn.close()


async def add_index_snapshot(event_id: str, t: str, value: float) -> None:
    conn = await get_db()
    try:
        await conn.execute(
            "INSERT INTO index_snapshots (event_id, t, value) VALUES (?, ?, ?)",
            (event_id, t, value),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_index_history(event_id: str) -> list[dict]:
    conn = await get_db()
    try:
        cursor = await conn.execute(
            "SELECT t, value FROM index_snapshots WHERE event_id = ? ORDER BY t",
            (event_id,),
        )
        rows = await cursor.fetchall()
    finally:
        await conn.close()
    return [{"t": r[0], "index": r[1]} for r in rows]


async def resolve_event(event_id: str, resolution: str, explanation: Optional[str] = None) -> None:
    conn = await get_db()
    try:
        await conn.execute(
            "UPDATE events SET status = 'resolved', resolution = ?, explanation = ? WHERE id = ?",
            (resolution, explanation or "", event_id),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_position(event_id: str) -> tuple[float, float]:
    conn = await get_db()
    try:
        cursor = await conn.execute(
            "SELECT net_up, net_down FROM event_positions WHERE event_id = ?",
            (event_id,),
        )
        row = await cursor.fetchone()
    finally:
        await conn.close()
    if not row:
        return 0.0, 0.0
    return row[0], row[1]


async def add_trade(event_id: str, side: str, amount: float) -> None:
    conn = await get_db()
    try:
        if side == "up":
            await conn.execute(
                "UPDATE event_positions SET net_up = net_up + ? WHERE event_id = ?",
                (amount, event_id),
            )
        else:
            await conn.execute(
                "UPDATE event_positions SET net_down = net_down + ? WHERE event_id = ?",
                (amount, event_id),
            )
        await conn.execute(
            "INSERT INTO trades (event_id, side, amount) VALUES (?, ?, ?)",
            (event_id, side, amount),
        )
        await conn.commit()
    finally:
        await conn.close()


async def set_event_status(event_id: str, status: str) -> None:
    conn = await get_db()
    try:
        await conn.execute(
            "UPDATE events SET status = ? WHERE id = ?", (status, event_id)
        )
        await conn.commit()
    finally:
        await conn.close()


async def update_event_on_accept(
    event_id: str,
    window_start: str,
    window_end: str,
    index_start: float,
    index_current: float,
    config: dict,
) -> None:
    """Set event to open and set window/index/config (after propose flow accepts)."""
    conn = await get_db()
    try:
        await conn.execute(
            """UPDATE events SET status = 'open', window_start = ?, window_end = ?,
               index_start = ?, index_current = ?, config = ? WHERE id = ?""",
            (window_start, window_end, index_start, index_current, json.dumps(config), event_id),
        )
        await conn.commit()
    finally:
        await conn.close()


async def update_event_on_reject(event_id: str, config: dict) -> None:
    """Set event to rejected and persist config."""
    conn = await get_db()
    try:
        await conn.execute(
            "UPDATE events SET status = 'rejected', config = ? WHERE id = ?",
            (json.dumps(config), event_id),
        )
        await conn.commit()
    finally:
        await conn.close()
