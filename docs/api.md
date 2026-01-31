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
| POST | `/events/:id/trade` | Submit belief (side + amount); demo credits only |
| GET | `/events/:id/explanation` | Short text "why index moved" (after resolution) |

---

## Request / Response Shapes

### POST /events (Propose event)

**Request body:**
```json
{
  "name": "Cursor Hackathon Dec 24",
  "windowMinutes": 60,
  "sourceUrl": "https://reddit.com/r/cursor/...",
  "description": "Optional short context"
}
```

- `name` (required), `windowMinutes` (required).
- `sourceUrl` (optional): e.g. Reddit URL.
- `description` (optional): short context if no URL.

Backend runs: initial reasonability check (Gemini + Google Search when `GEMINI_API_KEY` set), agent tool selection, index build (e.g. Hacker News via Algolia), then traction gate and accept decision. Event is stored as `proposed` during analysis, then set to `open` (accepted) or `rejected`.

**Response:** `201 Created`  
Body: full **Event** object (see below). `status` is `open` (accepted, ready to trade), `rejected` (not accepted), or `proposed` (if returned before accept/reject).

When `status` is `rejected`, the response includes **`rejectReason`** (string). Common cases:
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
  "rejectReason": "Optional; present when status is rejected."
}
```

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

### POST /events/:id/trade

**Request body:**
```json
{
  "side": "up" | "down",
  "amount": 10
}
```

- `amount`: demo credits (positive number).

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

## Errors

- `400` — Invalid body or params (e.g. missing `name`, invalid `side`).
- `404` — Event not found.
- `409` — e.g. trade on resolved event.

Body shape: `{ "detail": "string" }`.
