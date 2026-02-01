/**
 * API client matching docs/api.md. Uses /api prefix (proxied to backend in dev).
 */
const BASE = "/api";

export interface Event {
  id: string;
  name: string;
  status: "draft" | "proposed" | "open" | "rejected" | "resolved";
  windowStart: string;
  windowEnd: string;
  indexStart: number;
  indexCurrent: number;
  resolution: "up" | "down" | null;
  priceUp: number;
  priceDown: number;
  createdAt: string;
  /** Canonical market type: 1h (default) or 24h. */
  marketType?: "1h" | "24h";
  /** True when this is a demo market (accelerated dynamics, synthetic index). */
  demo?: boolean;
  /** Total traded volume (sum of amounts). */
  volume?: number;
  /** AI-generated emotional headline (e.g. "Is Clawdbot gaining momentum?"). */
  headline?: string | null;
  /** Precise subline (e.g. "Attention change · next 60 min"). */
  subline?: string | null;
  /** Button label for up side (e.g. "Heating up"). */
  labelUp?: string | null;
  /** Button label for down side (e.g. "Cooling down"). */
  labelDown?: string | null;
  /** Optional thumbnail/image URL for event card. */
  imageUrl?: string | null;
  /** Present when status is "rejected". */
  rejectReason?: string;
}

export interface IndexHistoryPoint {
  t: string;
  index: number;
}

export interface ProfileTrade {
  eventId: string;
  eventName: string;
  side: "up" | "down";
  amount: number;
  createdAt: string;
  status: string;
  resolution: "up" | "down" | null;
}

/** Propose an event: backend runs reasonability check (Gemini + Google Search), agent, index build, accept decision. */
export async function proposeEvent(
  name: string,
  options?: {
    sourceUrl?: string;
    description?: string;
    marketType?: "1h" | "24h";
    demo?: boolean;
  }
): Promise<Event> {
  const body: Record<string, unknown> = { name };
  if (options?.sourceUrl) body.sourceUrl = options.sourceUrl;
  if (options?.description) body.description = options.description;
  if (options?.marketType) body.marketType = options.marketType;
  if (options?.demo) body.demo = options.demo;
  const res = await fetch(`${BASE}/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new Error(d.detail || res.statusText);
  }
  return res.json();
}

export async function suggestWindowMinutes(params: {
  name: string;
  sourceUrl?: string;
  description?: string;
}): Promise<{ suggestedWindowMinutes: number }> {
  const res = await fetch(`${BASE}/events/suggest-window`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: params.name,
      sourceUrl: params.sourceUrl,
      description: params.description,
    }),
  });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new Error(d.detail || res.statusText);
  }
  return res.json();
}

export async function listEvents(params?: {
  status?: "open" | "resolved";
  name?: string;
  q?: string;
}): Promise<{ events: Event[] }> {
  const search = new URLSearchParams();
  if (params?.status) search.set("status", params.status);
  if (params?.name?.trim()) search.set("name", params.name.trim());
  if (params?.q?.trim()) search.set("q", params.q.trim());
  const query = search.toString() ? `?${search}` : "";
  const res = await fetch(`${BASE}/events${query}`);
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
  amount: number,
  traderId?: string
): Promise<{ ok: boolean; priceUp: number; priceDown: number }> {
  const body: Record<string, unknown> = { side, amount };
  if (traderId) body.trader_id = traderId;
  const res = await fetch(`${BASE}/events/${eventId}/trade`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new Error(d.detail || res.statusText);
  }
  return res.json();
}

export async function getProfileTrades(
  traderId: string
): Promise<{ trades: ProfileTrade[] }> {
  const res = await fetch(
    `${BASE}/profile/trades?trader_id=${encodeURIComponent(traderId)}`
  );
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

export async function getExplanation(
  eventId: string
): Promise<{ explanation: string | null }> {
  const res = await fetch(`${BASE}/events/${eventId}/explanation`);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

export async function getMarketContext(
  eventId: string
): Promise<{ context: string | null }> {
  const res = await fetch(`${BASE}/events/${eventId}/market-context`);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

export interface EventComment {
  id: number;
  eventId: string;
  traderId?: string | null;
  displayName?: string | null;
  body: string;
  createdAt: string;
}

export async function getEventComments(
  eventId: string
): Promise<{ comments: EventComment[] }> {
  const res = await fetch(`${BASE}/events/${eventId}/comments`);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

export async function postComment(
  eventId: string,
  body: { text: string; traderId?: string; displayName?: string }
): Promise<EventComment> {
  const res = await fetch(`${BASE}/events/${eventId}/comments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new Error(d.detail || res.statusText);
  }
  return res.json();
}
