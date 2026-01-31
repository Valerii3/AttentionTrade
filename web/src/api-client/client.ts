/**
 * API client matching docs/api.md. Uses /api prefix (proxied to backend in dev).
 */
const BASE = "/api";

export interface Event {
  id: string;
  name: string;
  status: "draft" | "open" | "resolved";
  windowStart: string;
  windowEnd: string;
  indexStart: number;
  indexCurrent: number;
  resolution: "up" | "down" | null;
  priceUp: number;
  priceDown: number;
  createdAt: string;
}

export interface IndexHistoryPoint {
  t: string;
  index: number;
}

export async function createEvent(name: string, windowMinutes: number): Promise<Event> {
  const res = await fetch(`${BASE}/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, windowMinutes }),
  });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new Error(d.detail || res.statusText);
  }
  return res.json();
}

export async function listEvents(status?: "open" | "resolved"): Promise<{ events: Event[] }> {
  const q = status ? `?status=${status}` : "";
  const res = await fetch(`${BASE}/events${q}`);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

export async function getEvent(id: string): Promise<Event> {
  const res = await fetch(`${BASE}/events/${id}`);
  if (!res.ok) {
    if (res.status === 404) throw new Error("Event not found");
    throw new Error(res.statusText);
  }
  return res.json();
}

export async function getIndexHistory(id: string): Promise<{ history: IndexHistoryPoint[] }> {
  const res = await fetch(`${BASE}/events/${id}/index-history`);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

export async function trade(
  eventId: string,
  side: "up" | "down",
  amount: number
): Promise<{ ok: boolean; priceUp: number; priceDown: number }> {
  const res = await fetch(`${BASE}/events/${eventId}/trade`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ side, amount }),
  });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new Error(d.detail || res.statusText);
  }
  return res.json();
}

export async function getExplanation(
  eventId: string
): Promise<{ explanation: string | null }> {
  const res = await fetch(`${BASE}/events/${eventId}/explanation`);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}
