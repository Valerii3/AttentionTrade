import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getEvent,
  getIndexHistory,
  listEvents,
  trade,
  getExplanation,
  getEventComments,
  postComment,
  type Event,
  type IndexHistoryPoint,
  type EventComment,
} from "@/api-client/client";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatCanonicalQuestion } from "@/lib/utils";
import { useProfile } from "@/contexts/profile-context";

const POLL_MS = 30000;

export default function EventDetail() {
  const { id } = useParams<{ id: string }>();
  const [event, setEvent] = useState<Event | null>(null);
  const [history, setHistory] = useState<IndexHistoryPoint[]>([]);
  const [pastWindows, setPastWindows] = useState<Event[]>([]);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [comments, setComments] = useState<EventComment[]>([]);
  const [commentText, setCommentText] = useState("");
  const [commentSubmitting, setCommentSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [tradeSide, setTradeSide] = useState<"up" | "down">("up");
  const [tradeAmount, setTradeAmount] = useState(10);
  const [trading, setTrading] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    if (!id) return;
    try {
      const [e, h] = await Promise.all([
        getEvent(id),
        getIndexHistory(id),
      ]);
      setEvent(e);
      setHistory(h.history);
      if (e.status === "resolved") {
        const ex = await getExplanation(id);
        setExplanation(ex.explanation);
      }
      const { comments: commentList } = await getEventComments(id);
      setComments(commentList);
      // Past windows for this topic (resolved, same name; exclude current id)
      const { events: resolvedSameTopic } = await listEvents({
        status: "resolved",
        name: e.name,
      });
      setPastWindows(
        resolvedSameTopic
          .filter((ev) => ev.id !== id)
          .sort(
            (a, b) =>
              new Date(b.windowEnd).getTime() - new Date(a.windowEnd).getTime()
          )
          .slice(0, 10)
      );
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

  const { profile } = useProfile();
  const traderId = profile?.traderId;
  const displayName = profile?.displayName;

  async function handleCommentSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!id || !commentText.trim()) return;
    setCommentSubmitting(true);
    try {
      await postComment(id, {
        text: commentText.trim(),
        traderId,
        displayName: displayName || undefined,
      });
      setCommentText("");
      const { comments: commentList } = await getEventComments(id);
      setComments(commentList);
    } finally {
      setCommentSubmitting(false);
    }
  }

  async function handleTrade(e: React.FormEvent) {
    e.preventDefault();
    if (!id || !event || event.status !== "open") return;
    setError("");
    setTrading(true);
    try {
      await trade(id, tradeSide, tradeAmount, traderId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Trade failed");
    } finally {
      setTrading(false);
    }
  }

  if (loading && !event)
    return (
      <div className="p-6 text-muted-foreground">Loading…</div>
    );
  if (!event)
    return (
      <div className="p-6">
        <p className="text-muted-foreground">
          Event not found. <Link to="/">Back to list</Link>.
        </p>
      </div>
    );

  const chartData = history.map(({ t, index }) => ({
    time: new Date(t).toLocaleTimeString(),
    index,
  }));

  return (
    <div className="p-4 md:p-6 max-w-3xl">
      <div className="mb-6">
        <Link
          to="/"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Events
        </Link>
      </div>

      <div className="bg-card rounded-lg border border-border p-6 relative">
        <div className="flex gap-4 mb-2">
          <img
            src={event.imageUrl || "/event-thumbnail-placeholder.png"}
            alt=""
            className="w-16 h-16 rounded-lg object-cover shrink-0 bg-muted"
          />
          <div className="min-w-0 flex-1">
            <h1 className="text-xl font-semibold text-foreground">
              {event.headline ?? formatCanonicalQuestion(event.name, event.marketType ?? "1h")}
            </h1>
            {event.subline && (
              <p className="text-sm text-muted-foreground mt-0.5">{event.subline}</p>
            )}
          </div>
        </div>
        {event.demo && (
          <p className="text-xs text-muted-foreground mt-1">
            Demo: accelerated attention dynamics.
          </p>
        )}
        <div className="text-sm text-muted-foreground mt-2">
          Status: <strong className="text-foreground">{event.status}</strong> ·
          Index: {event.indexCurrent.toFixed(1)} (start: {event.indexStart})
          {event.status === "open" && (
            <>
              {" "}
              · {event.labelUp ?? "Heating up"} {(event.priceUp * 100).toFixed(0)}% / {event.labelDown ?? "Cooling down"}{" "}
              {(event.priceDown * 100).toFixed(0)}%
            </>
          )}
          {event.status === "open" && event.volume != null && (
            <> · Vol. {event.volume}</>
          )}
          {event.status === "resolved" && event.resolution && (
            <>
              {" "}
              · Resolved: {event.resolution === "up" ? (event.labelUp ?? "Heating up") : (event.labelDown ?? "Cooling down")}
            </>
          )}
        </div>

        {history.length > 0 && (
          <div className="h-[240px] mt-6 rounded-lg border border-border bg-muted/30 p-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <XAxis
                  dataKey="time"
                  stroke="var(--muted-foreground)"
                  fontSize={12}
                />
                <YAxis
                  stroke="var(--muted-foreground)"
                  fontSize={12}
                  domain={["auto", "auto"]}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--card)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius)",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="index"
                  stroke="var(--primary)"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {event.status === "open" && (
          <form onSubmit={handleTrade} className="mt-6">
            <h3 className="text-sm font-medium text-foreground mb-3">
              Trade (demo credits)
            </h3>
            <div className="flex flex-wrap items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="side"
                  checked={tradeSide === "up"}
                  onChange={() => setTradeSide("up")}
                  className="accent-primary"
                />
                <span className="text-sm">{event.labelUp ?? "Heating up"}</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="side"
                  checked={tradeSide === "down"}
                  onChange={() => setTradeSide("down")}
                  className="accent-primary"
                />
                <span className="text-sm">{event.labelDown ?? "Cooling down"}</span>
              </label>
              <Input
                type="number"
                min={1}
                value={tradeAmount}
                onChange={(e) =>
                  setTradeAmount(Number(e.target.value) || 1)
                }
                className="w-20"
              />
              <Button type="submit" disabled={trading}>
                {trading ? "Trading…" : "Trade"}
              </Button>
            </div>
            {error && (
              <p className="text-sm text-destructive mt-2">{error}</p>
            )}
          </form>
        )}

        {event.status === "resolved" && explanation && (
          <div className="mt-6 p-4 rounded-lg border border-border bg-muted/30">
            <h3 className="text-sm font-medium text-foreground mb-2">
              Why attention moved
            </h3>
            <p className="text-sm text-muted-foreground">{explanation}</p>
          </div>
        )}

        {pastWindows.length > 0 && (
          <div className="mt-6 p-4 rounded-lg border border-border bg-muted/30">
            <h3 className="text-sm font-medium text-foreground mb-2">
              Past windows (recurring)
            </h3>
            <p className="text-sm text-muted-foreground mb-2">
              Resolution history for this topic:
            </p>
            <div className="flex flex-wrap gap-2">
              {pastWindows.map((w) => (
                <span
                  key={w.id}
                  className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-muted text-foreground"
                  title={new Date(w.windowEnd).toLocaleString()}
                >
                  {w.resolution === "up" ? "↑" : "↓"}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="mt-6 p-4 rounded-lg border border-border bg-muted/30">
          <h3 className="text-sm font-medium text-foreground mb-3">
            Comments
          </h3>
          <form onSubmit={handleCommentSubmit} className="mb-4">
            <textarea
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder="Add a comment…"
              rows={2}
              className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring mb-2"
            />
            <Button type="submit" disabled={commentSubmitting || !commentText.trim()}>
              {commentSubmitting ? "Posting…" : "Post"}
            </Button>
          </form>
          <div className="space-y-3">
            {comments.length === 0 ? (
              <p className="text-sm text-muted-foreground">No comments yet.</p>
            ) : (
              comments.map((c) => (
                <div
                  key={c.id}
                  className="text-sm border-b border-border pb-3 last:border-0 last:pb-0"
                >
                  <div className="flex items-center gap-2 text-muted-foreground mb-0.5">
                    <span className="font-medium text-foreground">
                      {c.displayName || "Anonymous"}
                    </span>
                    <span className="text-xs">
                      {new Date(c.createdAt).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-foreground whitespace-pre-wrap">{c.body}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
