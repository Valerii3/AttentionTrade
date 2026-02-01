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
  getMarketContext,
  getProfileTrades,
  type Event,
  type IndexHistoryPoint,
  type EventComment,
} from "@/api-client/client";
import { Button } from "@/components/ui/button";
import { formatCanonicalQuestion } from "@/lib/utils";
import { useProfile } from "@/contexts/profile-context";
import { MarketHeader, MarketFilters } from "@/components/market/market-header";
import { PriceChart, TIME_FRAMES, type Timeframe } from "@/components/market/price-chart";
import { TradingPanel } from "@/components/market/trading-panel";
import { CollapsibleSection } from "@/components/market/collapsible-section";
import { RulesSection } from "@/components/market/rules-section";

const POLL_MS = 30000;

function timeframeToInterval(tf: Timeframe): string | undefined {
  if (tf === "all") return undefined;
  return tf;
}

function formatChartTime(t: string, tf: Timeframe): string {
  const d = new Date(t);
  if (tf === "1h" || tf === "6h")
    return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  if (tf === "6m")
    return d.toLocaleDateString(undefined, { month: "short", year: "2-digit" });
  if (tf === "1d" || tf === "1w" || tf === "1m")
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  return d.toLocaleTimeString();
}

const DEFAULT_RULES =
  "This market resolves to Up if the attention index at window end is above the start value, otherwise Down. Index is built from real-time attention signals (e.g. discussion volume).";

const DEFAULT_EVENT_IMAGE = "/event-thumbnail-placeholder.png";

export default function EventDetail() {
  const { id } = useParams<{ id: string }>();
  const [event, setEvent] = useState<Event | null>(null);
  const [history, setHistory] = useState<IndexHistoryPoint[]>([]);
  const [timeframe, setTimeframe] = useState<Timeframe>("1d");
  const [pastWindows, setPastWindows] = useState<Event[]>([]);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [comments, setComments] = useState<EventComment[]>([]);
  const [commentText, setCommentText] = useState("");
  const [commentSubmitting, setCommentSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [tradeError, setTradeError] = useState("");
  const [marketContext, setMarketContext] = useState<string | null>(null);
  const [marketContextLoading, setMarketContextLoading] = useState(false);
  const [marketContextError, setMarketContextError] = useState<string | null>(
    null
  );
  const [positionUp, setPositionUp] = useState(0);
  const [positionDown, setPositionDown] = useState(0);

  const load = async () => {
    if (!id) return;
    const interval = timeframeToInterval(timeframe);
    try {
      const [e, h] = await Promise.all([
        getEvent(id),
        getIndexHistory(id, interval != null ? { interval } : undefined),
      ]);
      setEvent(e);
      setHistory(h.history);
      if (e.status === "resolved") {
        const ex = await getExplanation(id);
        setExplanation(ex.explanation);
      }
      const { comments: commentList } = await getEventComments(id);
      setComments(commentList);
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
  }, [id, timeframe]);

  const { profile, setBalance } = useProfile();
  const traderId = profile?.traderId;

  // Load position for this event when we have traderId
  useEffect(() => {
    if (!traderId || !id) return;
    getProfileTrades(traderId).then(({ trades }) => {
      let up = 0;
      let down = 0;
      for (const t of trades) {
        if (t.eventId !== id) continue;
        if (t.side === "up") up += t.amount;
        else down += t.amount;
      }
      setPositionUp(up);
      setPositionDown(down);
    }).catch(() => {});
  }, [traderId, id]);
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

  async function handleTrade(side: "up" | "down", amount: number) {
    if (!id || !event || event.status !== "open") return;
    setTradeError("");
    try {
      const result = await trade(id, side, amount, traderId);
      // Update balance if returned
      if (result.balance != null) {
        setBalance(result.balance);
      }
      await load();
      // Refresh position after trade
      if (traderId) {
        const { trades } = await getProfileTrades(traderId);
        let up = 0;
        let down = 0;
        for (const t of trades) {
          if (t.eventId !== id) continue;
          if (t.side === "up") up += t.amount;
          else down += t.amount;
        }
        setPositionUp(up);
        setPositionDown(down);
      }
    } catch (err) {
      setTradeError(err instanceof Error ? err.message : "Trade failed");
    }
  }

  async function handleGenerateMarketContext() {
    if (!id) return;
    setMarketContextLoading(true);
    setMarketContextError(null);
    setMarketContext(null);
    try {
      const { context } = await getMarketContext(id);
      setMarketContext(context);
      if (context == null) {
        setMarketContextError("Unable to generate. Try again.");
      }
    } catch {
      setMarketContextError("Request failed. Try again.");
    } finally {
      setMarketContextLoading(false);
    }
  }

  const netSize = Math.abs(positionUp - positionDown);
  const showSettledPosition =
    event?.status === "resolved" &&
    event?.resolution != null &&
    netSize > 0;
  const settledPnl = showSettledPosition
    ? event!.resolution === (positionUp >= positionDown ? "up" : "down")
      ? netSize
      : -netSize
    : 0;

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
    time: formatChartTime(t, timeframe),
    index,
  }));

  const title =
    event.headline ??
    formatCanonicalQuestion(event.name, event.marketType ?? "1h");
  const badge = event.marketType ?? "1h";
  const rulesText = event.subline
    ? `${event.subline}. ${DEFAULT_RULES}`
    : DEFAULT_RULES;

  return (
    <div className="min-h-screen bg-background">
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="mb-4">
          <Link
            to="/"
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            ← Events
          </Link>
        </div>

        <div className="flex gap-6">
          <div className="flex-1 min-w-0">
            <div className="flex items-start gap-4 mb-4">
              <img
                src={event.imageUrl || DEFAULT_EVENT_IMAGE}
                alt=""
                className="w-20 h-20 rounded-lg object-cover shrink-0 bg-muted"
              />
              <div className="min-w-0 flex-1">
                <MarketHeader title={title} badge={badge} />
              </div>
            </div>
            {event.demo && (
              <p className="text-xs text-muted-foreground mt-2">
                Demo: accelerated attention dynamics.
              </p>
            )}
            <MarketFilters
              windowEnd={event.windowEnd}
              pastWindowsCount={pastWindows.length}
            />

            {chartData.length > 0 && (
              <PriceChart
                data={chartData}
                priceUp={event.priceUp ?? 0.5}
                priceDown={event.priceDown ?? 0.5}
                labelUp={event.labelUp}
                labelDown={event.labelDown}
                volume={event.volume}
                windowEnd={event.windowEnd}
                timeframe={timeframe}
                onTimeframeChange={setTimeframe}
              />
            )}

            <div className="mt-6 space-y-3">
              <CollapsibleSection
                title="Market context"
                defaultOpen={false}
                action={{
                  label: "Generate",
                  onClick: handleGenerateMarketContext,
                  loading: marketContextLoading,
                }}
              >
                {marketContextLoading && !marketContext && (
                  <p className="text-sm text-muted-foreground">
                    Generating context…
                  </p>
                )}
                {marketContextError && (
                  <p className="text-sm text-destructive">{marketContextError}</p>
                )}
                {marketContext && (
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {marketContext}
                  </p>
                )}
                {!marketContext &&
                  !marketContextLoading &&
                  !marketContextError && (
                    <p className="text-sm text-muted-foreground">
                      Click Generate to get an AI summary of what’s driving
                      attention (Gemini + web search).
                    </p>
                  )}
              </CollapsibleSection>
            </div>

            <RulesSection rules={rulesText} />

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
                <Button
                  type="submit"
                  disabled={commentSubmitting || !commentText.trim()}
                >
                  {commentSubmitting ? "Posting…" : "Post"}
                </Button>
              </form>
              <div className="space-y-3">
                {comments.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No comments yet.
                  </p>
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
                      <p className="text-foreground whitespace-pre-wrap">
                        {c.body}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {event.status === "open" && (
            <div className="hidden lg:block shrink-0">
              <div className="sticky top-6">
                <TradingPanel
                  priceUp={event.priceUp ?? 0.5}
                  priceDown={event.priceDown ?? 0.5}
                  labelUp={event.labelUp}
                  labelDown={event.labelDown}
                  disabled={false}
                  onTrade={handleTrade}
                  error={tradeError || undefined}
                  positionUp={positionUp}
                  positionDown={positionDown}
                />
              </div>
            </div>
          )}

          {showSettledPosition && (
            <div className="hidden lg:block shrink-0">
              <div className="sticky top-6 p-4 rounded-lg border border-border bg-card">
                <h3 className="text-sm font-medium text-foreground mb-2">
                  Your position
                </h3>
                <p
                  className={`text-xl font-semibold ${
                    settledPnl >= 0 ? "text-success" : "text-destructive"
                  }`}
                >
                  Position settled: {settledPnl >= 0 ? "+" : ""}
                  {settledPnl}
                </p>
                <p
                  className={`text-sm font-medium mt-1 ${
                    settledPnl >= 0 ? "text-success" : "text-destructive"
                  }`}
                >
                  {settledPnl >= 0 ? "Won" : "Lost"}
                </p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
