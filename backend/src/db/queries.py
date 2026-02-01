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
    conn = await get_db()
    try:
        # Migration first: add trader_id to existing trades table if missing (so schema's CREATE INDEX succeeds)
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='trades'"
        )
        has_trades = (await cursor.fetchone()) is not None
        if has_trades:
            cursor = await conn.execute("PRAGMA table_info(trades)")
            columns = [row[1] for row in await cursor.fetchall()]
            if "trader_id" not in columns:
                await conn.execute("ALTER TABLE trades ADD COLUMN trader_id TEXT")
                await conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_trades_trader ON trades(trader_id)"
                )
        await conn.commit()

        # Migration: add trader_id / display_name to event_comments if missing
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='event_comments'"
        )
        has_comments = (await cursor.fetchone()) is not None
        if has_comments:
            cursor = await conn.execute("PRAGMA table_info(event_comments)")
            columns = [row[1] for row in await cursor.fetchall()]
            if "trader_id" not in columns:
                await conn.execute("ALTER TABLE event_comments ADD COLUMN trader_id TEXT")
            if "display_name" not in columns:
                await conn.execute("ALTER TABLE event_comments ADD COLUMN display_name TEXT")
        await conn.commit()

        with open(SCHEMA_PATH) as f:
            schema = f.read()
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


async def list_events(
    status: Optional[str] = None,
    name: Optional[str] = None,
    q: Optional[str] = None,
) -> list[dict]:
    conn = await get_db()
    try:
        search_term = q.strip() if q else None
        conditions = []
        params = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if name:
            conditions.append("name = ?")
            params.append(name)
        if search_term:
            conditions.append("LOWER(name) LIKE '%' || LOWER(?) || '%'")
            params.append(search_term)
        where = " AND ".join(conditions) if conditions else "1=1"
        cursor = await conn.execute(
            f"SELECT * FROM events WHERE {where} ORDER BY created_at DESC",
            tuple(params),
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


async def list_comments(event_id: str) -> list[dict]:
    """Return comments for an event, newest first."""
    conn = await get_db()
    try:
        cursor = await conn.execute(
            """
            SELECT id, event_id, trader_id, display_name, body, created_at
            FROM event_comments
            WHERE event_id = ?
            ORDER BY created_at DESC
            """,
            (event_id,),
        )
        rows = await cursor.fetchall()
    finally:
        await conn.close()
    columns = ["id", "event_id", "trader_id", "display_name", "body", "created_at"]
    return [dict(zip(columns, row)) for row in rows]


async def add_comment(
    event_id: str,
    body: str,
    trader_id: Optional[str] = None,
    display_name: Optional[str] = None,
) -> dict:
    """Insert a comment and return the created row."""
    conn = await get_db()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO event_comments (event_id, trader_id, display_name, body)
            VALUES (?, ?, ?, ?)
            """,
            (event_id, trader_id, display_name or None, body),
        )
        await conn.commit()
        row_id = cursor.lastrowid
        cursor = await conn.execute(
            """
            SELECT id, event_id, trader_id, display_name, body, created_at
            FROM event_comments WHERE id = ?
            """,
            (row_id,),
        )
        row = await cursor.fetchone()
    finally:
        await conn.close()
    columns = ["id", "event_id", "trader_id", "display_name", "body", "created_at"]
    return dict(zip(columns, row))


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


async def add_index_snapshots_batch(
    event_id: str, points: list[tuple[str, float]]
) -> None:
    """Insert multiple index snapshots (e.g. 6-month backfill)."""
    if not points:
        return
    conn = await get_db()
    try:
        await conn.executemany(
            "INSERT INTO index_snapshots (event_id, t, value) VALUES (?, ?, ?)",
            [(event_id, t, value) for t, value in points],
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


async def get_volume(event_id: str) -> float:
    """Return total traded volume (sum of amounts) for this event."""
    conn = await get_db()
    try:
        cursor = await conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM trades WHERE event_id = ?",
            (event_id,),
        )
        row = await cursor.fetchone()
    finally:
        await conn.close()
    return float(row[0]) if row else 0.0


async def add_trade(
    event_id: str, side: str, amount: float, trader_id: Optional[str] = None
) -> None:
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
            "INSERT INTO trades (event_id, side, amount, trader_id) VALUES (?, ?, ?, ?)",
            (event_id, side, amount, trader_id),
        )
        await conn.commit()
    finally:
        await conn.close()


async def list_trades_by_trader(trader_id: str) -> list[dict]:
    """Return trades for a trader with event name, status, resolution (join with events)."""
    conn = await get_db()
    try:
        cursor = await conn.execute(
            """
            SELECT t.event_id, t.side, t.amount, t.created_at,
                   e.name AS event_name, e.status AS event_status, e.resolution
            FROM trades t
            JOIN events e ON e.id = t.event_id
            WHERE t.trader_id = ?
            ORDER BY t.created_at ASC
            """,
            (trader_id,),
        )
        rows = await cursor.fetchall()
    finally:
        await conn.close()
    return [
        {
            "event_id": r[0],
            "side": r[1],
            "amount": r[2],
            "created_at": r[3],
            "event_name": r[4],
            "event_status": r[5],
            "resolution": r[6],
        }
        for r in rows
    ]


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
