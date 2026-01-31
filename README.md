# Attention Markets

Trade cultural momentum, not outcomes. Real-time platform where users trade on whether *attention* around an event will rise or fade over short time windows.

## Structure

- **`web/`** — Frontend (Vite + React + TypeScript). Person 1.
- **`backend/`** — API (FastAPI). Database: **SQLite** (single file, no server). Person 2.
- **`agent/`** — AI: event definition (channels, keywords, exclusions) and resolution explanations. Person 2.
- **`docs/api.md`** — API contract.

## Run locally

### Backend

From the **project root** (AttentionTrade/):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd ..
uvicorn backend.src.main:app --reload --host 0.0.0.0 --port 8000
```

The API runs at `http://localhost:8000`. The **SQLite** DB file is `attention.db` in the project root (or set `ATTENTION_DB_PATH`).

### Web

In another terminal, from project root:

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:5173`. The dev server proxies `/api` to `http://localhost:8000`.

## Environment variables

- **Backend / Agent**
  - `ATTENTION_DB_PATH` — SQLite database file path (default: `attention.db` in project root).
  - `OPENAI_API_KEY` — Optional. If set, the agent uses the LLM for event definition and resolution explanations; otherwise it uses simple defaults.

## API

See [docs/api.md](docs/api.md) for endpoints and request/response shapes.

## Features

- Create events with name and time window; AI defines channels/keywords/exclusions (or defaults).
- Index updates every 1 minute from Hacker News (and placeholder Reddit); index = 100 + 10 × normalized delta.
- Trade “Attention ↑” or “Attention ↓” with demo credits; belief-based pricing (sigmoid).
- When the window ends, event resolves to up/down and an optional AI explanation is stored.
