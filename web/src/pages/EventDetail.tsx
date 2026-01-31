import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getEvent,
  getIndexHistory,
  trade,
  getExplanation,
  type Event,
  type IndexHistoryPoint,
} from "../api-client/client";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const POLL_MS = 30000;

export default function EventDetail() {
  const { id } = useParams<{ id: string }>();
  const [event, setEvent] = useState<Event | null>(null);
  const [history, setHistory] = useState<IndexHistoryPoint[]>([]);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tradeSide, setTradeSide] = useState<"up" | "down">("up");
  const [tradeAmount, setTradeAmount] = useState(10);
  const [trading, setTrading] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    if (!id) return;
    try {
      const [e, h] = await Promise.all([getEvent(id), getIndexHistory(id)]);
      setEvent(e);
      setHistory(h.history);
      if (e.status === "resolved") {
        const ex = await getExplanation(id);
        setExplanation(ex.explanation);
      }
    } catch {
      setEvent(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, POLL_MS);
    return () => clearInterval(t);
  }, [id]);

  async function handleTrade(e: React.FormEvent) {
    e.preventDefault();
    if (!id || !event || event.status !== "open") return;
    setError("");
    setTrading(true);
    try {
      await trade(id, tradeSide, tradeAmount);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Trade failed");
    } finally {
      setTrading(false);
    }
  }

  if (loading && !event) return <p>Loading…</p>;
  if (!event) return <p>Event not found. <Link to="/">Back to list</Link>.</p>;

  const chartData = history.map(({ t, index }) => ({
    time: new Date(t).toLocaleTimeString(),
    index,
  }));

  return (
    <div>
      <div style={{ marginBottom: "1rem" }}>
        <Link to="/">← Events</Link>
      </div>
      <h1 style={{ marginTop: 0 }}>{event.name}</h1>
      <div style={{ color: "#71717a", marginBottom: "1rem" }}>
        Status: <strong>{event.status}</strong> · Index: {event.indexCurrent.toFixed(1)} (start: {event.indexStart})
        {event.status === "open" && (
          <> · Up {(event.priceUp * 100).toFixed(0)}% / Down {(event.priceDown * 100).toFixed(0)}%</>
        )}
        {event.status === "resolved" && event.resolution && (
          <> · Resolved: Attention {event.resolution === "up" ? "↑" : "↓"}</>
        )}
      </div>

      {history.length > 0 && (
        <div style={{ height: 240, marginBottom: "1.5rem", background: "#18181b", borderRadius: "8px", padding: "0.5rem" }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <XAxis dataKey="time" stroke="#71717a" fontSize={12} />
              <YAxis stroke="#71717a" fontSize={12} domain={["auto", "auto"]} />
              <Tooltip contentStyle={{ background: "#27272a", border: "1px solid #3f3f46" }} />
              <Line type="monotone" dataKey="index" stroke="#a78bfa" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {event.status === "open" && (
        <form onSubmit={handleTrade} style={{ marginBottom: "1.5rem" }}>
          <h3 style={{ marginTop: 0 }}>Trade (demo credits)</h3>
          <div style={{ display: "flex", gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
            <label>
              <input
                type="radio"
                name="side"
                checked={tradeSide === "up"}
                onChange={() => setTradeSide("up")}
              />{" "}
              Attention ↑
            </label>
            <label>
              <input
                type="radio"
                name="side"
                checked={tradeSide === "down"}
                onChange={() => setTradeSide("down")}
              />{" "}
              Attention ↓
            </label>
            <input
              type="number"
              min={1}
              value={tradeAmount}
              onChange={(e) => setTradeAmount(Number(e.target.value) || 1)}
              style={{
                width: 80,
                padding: "0.25rem 0.5rem",
                background: "#27272a",
                border: "1px solid #3f3f46",
                color: "#e4e4e7",
                borderRadius: "4px",
              }}
            />
            <button
              type="submit"
              disabled={trading}
              style={{
                padding: "0.25rem 0.75rem",
                background: "#7c3aed",
                color: "#fff",
                border: "none",
                borderRadius: "4px",
                cursor: trading ? "not-allowed" : "pointer",
              }}
            >
              {trading ? "Trading…" : "Trade"}
            </button>
          </div>
          {error && <p style={{ color: "#f87171", marginTop: "0.5rem" }}>{error}</p>}
        </form>
      )}

      {event.status === "resolved" && explanation && (
        <div
          style={{
            padding: "1rem",
            background: "#18181b",
            borderRadius: "8px",
            border: "1px solid #27272a",
          }}
        >
          <h3 style={{ marginTop: 0 }}>Why attention moved</h3>
          <p style={{ margin: 0, color: "#a1a1aa" }}>{explanation}</p>
        </div>
      )}
    </div>
  );
}
