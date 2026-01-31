import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listEvents, type Event } from "../api-client/client";

export default function EventList() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"open" | "resolved" | "">("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const status = filter === "" ? undefined : filter;
        const { events: list } = await listEvents(status);
        if (!cancelled) setEvents(list);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [filter]);

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Events</h1>
      <p style={{ color: "#71717a", marginBottom: "1rem" }}>
        Trade on whether attention will rise or fade.
      </p>
      <div style={{ marginBottom: "1rem" }}>
        <label>
          Filter:{" "}
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as "open" | "resolved" | "")}
            style={{ padding: "0.25rem 0.5rem", background: "#27272a", color: "#e4e4e7", border: "1px solid #3f3f46" }}
          >
            <option value="">All</option>
            <option value="open">Open</option>
            <option value="resolved">Resolved</option>
          </select>
        </label>
      </div>
      {loading ? (
        <p>Loading…</p>
      ) : events.length === 0 ? (
        <p>No events yet. <Link to="/create">Create one</Link>.</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {events.map((e) => (
            <li
              key={e.id}
              style={{
                padding: "1rem",
                marginBottom: "0.5rem",
                background: "#18181b",
                borderRadius: "8px",
                border: "1px solid #27272a",
              }}
            >
              <Link to={`/events/${e.id}`} style={{ fontWeight: 600, color: "#e4e4e7" }}>
                {e.name}
              </Link>
              <div style={{ fontSize: "0.875rem", color: "#71717a", marginTop: "0.25rem" }}>
                Status: {e.status} · Index: {e.indexCurrent.toFixed(1)} ·{" "}
                {e.status === "open" && (
                  <>Up {((e.priceUp ?? 0.5) * 100).toFixed(0)}% / Down {((e.priceDown ?? 0.5) * 100).toFixed(0)}%</>
                )}
                {e.status === "resolved" && e.resolution && (
                  <>Resolved: Attention {e.resolution === "up" ? "↑" : "↓"}</>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
