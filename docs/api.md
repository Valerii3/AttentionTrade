# Attention Markets API Contract

Base URL: `http://localhost:8000` (or set via env).

---

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/events` | Create event; backend calls agent for channels/keywords/exclusions |
| GET | `/events` | List events (optional query: `?status=open` or `?status=resolved`) |
| GET | `/events/:id` | Event detail + current index, window, resolution, prices |
| GET | `/events/:id/index-history` | Time series for chart |
| POST | `/events/:id/trade` | Submit belief (side + amount); demo credits only |
| GET | `/events/:id/explanation` | Short text "why index moved" (after resolution) |

---

## Request / Response Shapes

### POST /events

**Request body:**
```json
{
  "name": "Cursor Hackathon Dec 24",
  "windowMinutes": 60
}
```

**Response:** `201 Created`  
Body: full **Event** object (see below).

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
  "status": "draft" | "open" | "resolved",
  "windowStart": "ISO8601",
  "windowEnd": "ISO8601",
  "indexStart": 100,
  "indexCurrent": 105.2,
  "resolution": "up" | "down" | null,
  "priceUp": 0.52,
  "priceDown": 0.48,
  "createdAt": "ISO8601"
}
```

- `priceUp` + `priceDown` are in [0, 1] and sum to 1.
- `resolution` is set when status is `resolved`.

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
