-- Attention Markets schema (SQLite)

CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft',  -- draft | proposed | open | rejected | resolved
  window_start TEXT NOT NULL,
  window_end TEXT NOT NULL,
  index_start REAL NOT NULL DEFAULT 100,
  index_current REAL NOT NULL DEFAULT 100,
  resolution TEXT,  -- up | down
  config TEXT,  -- JSON: channels, keywords, exclusions
  explanation TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS index_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL REFERENCES events(id),
  t TEXT NOT NULL,
  value REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL REFERENCES events(id),
  side TEXT NOT NULL,  -- up | down
  amount REAL NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Net position per event for sigmoid pricing (derived from trades, or store running total)
CREATE TABLE IF NOT EXISTS event_positions (
  event_id TEXT PRIMARY KEY REFERENCES events(id),
  net_up REAL NOT NULL DEFAULT 0,
  net_down REAL NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_index_snapshots_event ON index_snapshots(event_id);
CREATE INDEX IF NOT EXISTS idx_trades_event ON trades(event_id);
