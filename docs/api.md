# Attention Markets API Contract

Base URL: `http://localhost:8000` (or set via env).

---

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/events` | Propose event; backend runs agent (tool selection, index build, accept decision). Returns event with status `open` (accepted) or `rejected`. |
| POST | `/events/suggest-window` | Get AI-suggested window duration (minutes) for name/URL/description |
| GET | `/events` | List events (optional query: `?status=open` or `?status=resolved`) |
| GET | `/events/:id` | Event detail + current index, window, resolution, prices |
| GET | `/events/:id/index-history` | Time series for chart |
| GET | `/events/:id/comments` | List comments for event (newest first) |
| POST | `/events/:id/comments` | Post a comment (body: `text`, optional `traderId`, `displayName`) |
| POST | `/events/:id/trade` | Submit belief (side + amount; optional `trader_id`); demo credits only |
| GET | `/events/:id/explanation` | Short text "why index moved" (after resolution) |
| GET | `/profile/trades` | List trades for a trader (query: `?trader_id=xxx`) |

---

## Request / Response Shapes

### POST /events (Propose event)

**Request body:**
```json
{
  "name": "Cursor Hackathon Dec 24",
  "marketType": "1h",
  "sourceUrl": "https://reddit.com/r/cursor/...",
  "description": "Optional short context"
}
```

- `name` (required): topic or event (e.g. "Cursor Hackathon Dec 24"). The displayed question is always a canonical template: 1h — "Will attention around {name} increase in the next 60 minutes?" or 24h — "Will attention around {name} remain elevated over the next 24 hours?"
- `marketType` (optional): `"1h"` (default) or `"24h"`. Determines window length and question template.
- `windowMinutes` (optional): ignored for normal flow; used only for demo override (e.g. 2 minutes).
- `demo` (optional): if `true`, create a demo market: 2-minute window, synthetic index (mean-reverting with momentum), tick every 15s. Must be labeled "Demo: accelerated attention dynamics" in the UI.
- `sourceUrl` (optional): e.g. Reddit URL.
- `description` (optional): short context if no URL.

Backend runs: initial reasonability check (Gemini + Google Search when `GEMINI_API_KEY` set), agent tool selection, index build (e.g. Hacker News via Algolia), then traction gate and accept decision. Event is stored as `proposed` during analysis, then set to `open` (accepted) or `rejected`. **Recurring:** When an event resolves, a new window for the same topic is opened automatically (unless the event is a demo). Resolved windows can be listed with `GET /events?status=resolved&name=TopicName` for history (e.g. ↑ ↓ ↑ ↑).

**Response:** `201 Created`  
Body: full **Event** object (see below). `status` is `open` (accepted, ready to trade), `rejected` (not accepted), or `proposed` (if returned before accept/reject).

When `status` is `rejected`, the response includes **`rejectReason`** (string). Common cases:
- **Attention-native only:** Events must be attention markets, not outcome markets. Outcome-style proposals (resolvable by checking one number, e.g. “Will X get 100 stars by Friday?” or “Will X hit N users?”) may be rejected with `rejectReason` explaining the rule and suggesting an attention framing (e.g. “Will attention around [topic] increase in the next 60 minutes?”).
- **Initial reasonability check failed** — e.g. no or insufficient information about the event on the web.
- **Insufficient attention (traction)** — total activity from selected channels (e.g. Hacker News) is below the traction threshold; the event is not tradable yet. Message is typically: *"There isn't enough attention for this event yet, so it's not tradable."*
- **Accept decision (Gemini)** — agent decided not to accept for trading; reason is in `rejectReason`.

---

### POST /events/suggest-window

**Request body:**
```json
{
  "name": "Cursor Hackathon Dec 24",
  "sourceUrl": "https://reddit.com/r/cursor/...",
  "description": "Optional short context"
}
```

- `name` (required). `sourceUrl` and `description` optional.

**Response:** `200 OK`  
Body:
```json
{
  "suggestedWindowMinutes": 60
}
```

---

### GET /events

**Query params (optional):**
- `status`: `open` | `resolved` — filter by status.
- `name`: filter by topic name (e.g. for resolution history per topic).
- `q`: search string; events whose name contains `q` (case-insensitive substring).

**Response:** `200 OK`  
Body:
```json
{
  "events": [
    { /* Event */ }
  ]
}
```

---

### GET /events/:id

**Response:** `200 OK`  
Body: single **Event** object.

**Event object:**
```json
{
  "id": "uuid",
  "name": "string",
  "status": "draft" | "proposed" | "open" | "rejected" | "resolved",
  "windowStart": "ISO8601",
  "windowEnd": "ISO8601",
  "indexStart": 100,
  "indexCurrent": 105.2,
  "resolution": "up" | "down" | null,
  "priceUp": 0.52,
  "priceDown": 0.48,
  "createdAt": "ISO8601",
  "marketType": "1h" | "24h",
  "demo": false,
  "rejectReason": "Optional; present when status is rejected."
}
```

- `name` is the topic; the canonical question is derived from `name` + `marketType`.
- `marketType`: `"1h"` (default) or `"24h"`.
- `demo`: `true` when this is a demo market (accelerated dynamics, synthetic index). Demo markets use 2-min windows and must be labeled in the UI (e.g. "Demo: accelerated attention dynamics").
- `priceUp` + `priceDown` are in [0, 1] and sum to 1.
- `resolution` is set when status is `resolved`.
- `rejectReason` is present when `status` is `rejected` (e.g. reasonability check failed, insufficient attention/traction, or accept decision).

---

### GET /events/:id/index-history

**Response:** `200 OK`  
Body:
```json
{
  "history": [
    { "t": "ISO8601", "index": 100 },
    { "t": "ISO8601", "index": 101.5 }
  ]
}
```

---

### GET /events/:id/comments

**Response:** `200 OK`  
Body: list of comments, **newest first**.
```json
{
  "comments": [
    {
      "id": 1,
      "eventId": "uuid",
      "traderId": "optional",
      "displayName": "optional",
      "body": "Comment text",
      "createdAt": "ISO8601"
    }
  ]
}
```

---

### POST /events/:id/comments

Allowed only when event status is `open` or `resolved`.

**Request body:**
```json
{
  "text": "Comment text",
  "traderId": "optional",
  "displayName": "optional"
}
```

- `text` (required): comment body.
- `traderId` (optional): from profile.
- `displayName` (optional): for display; if omitted, show as "Anonymous".

**Response:** `200 OK`  
Body: the created **Comment** object (same shape as in GET comments).

---

### POST /events/:id/trade

**Request body:**
```json
{
  "side": "up" | "down",
  "amount": 10,
  "trader_id": "optional-uuid"
}
```

- `side` (required): `"up"` or `"down"`.
- `amount` (required): demo credits (positive number).
- `trader_id` (optional): if provided, the trade is associated with this trader for the profile page.

**Response:** `200 OK`  
Body:
```json
{
  "ok": true,
  "priceUp": 0.55,
  "priceDown": 0.45
}
```

---

### GET /profile/trades

**Query params:**
- `trader_id` (required): UUID of the trader (e.g. from frontend localStorage).

**Response:** `200 OK`  
Body:
```json
{
  "trades": [
    {
      "eventId": "uuid",
      "eventName": "string",
      "side": "up" | "down",
      "amount": 10,
      "createdAt": "ISO8601",
      "status": "open" | "resolved",
      "resolution": "up" | "down" | null
    }
  ]
}
```

- `status` and `resolution` are from the event at response time; frontend can compute won/lost and PnL from these.

---

### GET /events/:id/explanation

**Response:** `200 OK`  
Body:
```json
{
  "explanation": "The spike was driven by a Hacker News post reaching the front page."
}
```

If no explanation yet (e.g. not resolved): `404` or `{ "explanation": null }`.

---

---

## Attention Index

The **Attention Index** is the resolution oracle for each event:

- **Definition:** It is computed from event config (keywords, tools) and channel data (e.g. Hacker News via Algolia, Reddit). The formula is in `backend/src/services/index_pipeline.py`: baseline 100, plus a weighted sum of log-scaled activity deltas.
- **Fixed per event:** The index is defined once per event by its config and channels; it does not change based on user input other than the event’s own configuration.
- **Independent of trading:** Trades and order book activity do not affect the index. The index is read-only for the market and is used only for resolution, explanation, and auditability.
- **Demo exception:** For demo events, the index may be synthetic (simulated) for accelerated dynamics; it is still independent of trading.

---

## Demo mode

Demo markets use **accelerated attention dynamics** for illustration:

- **Window:** 1–2 minutes (e.g. 2 minutes).
- **Index:** Synthetic (mean-reverting with momentum bursts), not live channel data. Deterministic for the same event and time; see `backend/src/services/demo_index.py`.
- **Tick:** Index is updated every 15 seconds (vs. 60 seconds for non-demo).
- **Label:** Must be shown in the UI: e.g. "Demo: accelerated attention dynamics" or "Demo markets use accelerated attention dynamics."
- **Recurring:** Demo events do not auto-open a next window after resolution.

Create a demo market by sending `demo: true` in the propose body.

---

## Errors

- `400` — Invalid body or params (e.g. missing `name`, invalid `side`).
- `404` — Event not found.
- `409` — e.g. trade on resolved event.

Body shape: `{ "detail": "string" }`.
