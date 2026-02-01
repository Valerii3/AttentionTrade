import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getProfileTrades, type ProfileTrade } from "@/api-client/client";
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
import { PROFILE_KEY } from "@/lib/profile";
import type { StoredProfile } from "@/lib/profile";
import { useProfile } from "@/contexts/profile-context";

/** One position per event: net exposure and outcome (Closed when user closed before resolution). */
interface PositionRow {
  eventId: string;
  eventName: string;
  status: string;
  resolution: "up" | "down" | null;
  netUp: number;
  netDown: number;
  netSize: number;
  netSide: "up" | "down";
  lastTradeAt: string;
  outcome: "Won" | "Lost" | "Open" | "Closed";
  pnl: number | null;
}

function tradesToPositions(trades: ProfileTrade[]): PositionRow[] {
  // Process trades in order per event to detect close trade and its execution_price
  const byEvent = new Map<
    string,
    {
      name: string;
      status: string;
      resolution: "up" | "down" | null;
      up: number;
      down: number;
      lastAt: string;
      /** When position was closed (net 0), execution_price of the close trade (opposite side). */
      closeExecutionPrice: number | null;
    }
  >();
  const sorted = [...trades].sort(
    (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
  );
  for (const t of sorted) {
    const cur = byEvent.get(t.eventId);
    const prevUp = cur?.up ?? 0;
    const prevDown = cur?.down ?? 0;
    const up = prevUp + (t.side === "up" ? t.amount : 0);
    const down = prevDown + (t.side === "down" ? t.amount : 0);
    const lastAt =
      !cur || new Date(t.createdAt).getTime() > new Date(cur.lastAt).getTime()
        ? t.createdAt
        : cur.lastAt;
    const closeExecutionPrice =
      up === down && (t.executionPrice != null)
        ? t.executionPrice
        : cur?.closeExecutionPrice ?? null;
    byEvent.set(t.eventId, {
      name: t.eventName,
      status: t.status,
      resolution: t.resolution ?? null,
      up,
      down,
      lastAt,
      closeExecutionPrice,
    });
  }
  const rows: PositionRow[] = [];
  for (const [eventId, p] of byEvent.entries()) {
    const netSize = Math.abs(p.up - p.down);
    const netSide: "up" | "down" = p.up >= p.down ? "up" : "down";
    let outcome: PositionRow["outcome"];
    let pnl: number | null;
    if (p.status === "resolved" && p.resolution != null) {
      outcome = p.resolution === netSide ? "Won" : "Lost";
      pnl = p.resolution === netSide ? netSize : -netSize;
    } else if (netSize === 0) {
      outcome = "Closed";
      // Realized PnL at close: value at close = closeAmount * sellPrice - closeAmount
      // Sell price for the side we were long: if we closed by buying Down, we were long Up, sellPrice = 1 - execution_price
      if (p.closeExecutionPrice != null) {
        // Close trade was on the opposite side. We were long netSide.
        // If we were long Up, we closed by buying Down: value = closeAmount * (1 - priceDown) = closeAmount * priceUp, so we need price at close. The close trade has execution_price = priceDown. So sellPrice (priceUp) = 1 - execution_price. PnL = closeAmount * (1 - execution_price) - closeAmount = -closeAmount * execution_price.
        // If we were long Down, we closed by buying Up: value = closeAmount * priceDown, close trade execution_price = priceUp. sellPrice = 1 - priceUp = priceDown. So PnL = closeAmount * (1 - execution_price) - closeAmount = -closeAmount * execution_price. Same formula!
        // Actually: value at close for our long side = amount * (price of our side at close). When we closed by buying opposite, execution_price = price of opposite. So price of our side = 1 - execution_price. Value = amount * (1 - execution_price). Cost = amount. PnL = amount * (1 - execution_price) - amount = -amount * execution_price.
        const closeAmount = p.up; // same as p.down when closed
        pnl = closeAmount * (1 - p.closeExecutionPrice) - closeAmount;
      } else {
        pnl = 0; // legacy closed position without execution_price
      }
    } else {
      outcome = "Open";
      pnl = null;
    }
    rows.push({
      eventId,
      eventName: p.name,
      status: p.status,
      resolution: p.resolution,
      netUp: p.up,
      netDown: p.down,
      netSize,
      netSide,
      lastTradeAt: p.lastAt,
      outcome,
      pnl,
    });
  }
  return rows.sort(
    (a, b) =>
      new Date(b.lastTradeAt).getTime() - new Date(a.lastTradeAt).getTime()
  );
}

export default function Profile() {
  const { profile, saveProfile, balance } = useProfile();
  const [trades, setTrades] = useState<ProfileTrade[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [editNameValue, setEditNameValue] = useState("");

  const fetchTrades = useCallback(() => {
    if (!profile?.traderId) return;
    setLoading(true);
    getProfileTrades(profile.traderId)
      .then((r) => setTrades(r.trades))
      .catch(() => setTrades([]))
      .finally(() => setLoading(false));
  }, [profile?.traderId]);

  useEffect(() => {
    if (!profile?.traderId) return;
    let cancelled = false;
    setLoading(true);
    getProfileTrades(profile.traderId)
      .then((r) => {
        if (!cancelled) setTrades(r.trades);
      })
      .catch(() => {
        if (!cancelled) setTrades([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [profile?.traderId]);

  // Refetch trades periodically and when tab gains focus so resolution updates appear
  useEffect(() => {
    if (!profile?.traderId) return;
    const interval = setInterval(fetchTrades, 45000);
    const onFocus = () => fetchTrades();
    window.addEventListener("focus", onFocus);
    return () => {
      clearInterval(interval);
      window.removeEventListener("focus", onFocus);
    };
  }, [profile?.traderId, fetchTrades]);

  const positions = useMemo(() => tradesToPositions(trades), [trades]);

  const totalPnl = useMemo(() => {
    return positions.reduce((sum, p) => sum + (p.pnl ?? 0), 0);
  }, [positions]);

  const pnlChartData = useMemo(() => {
    const sorted = [...positions].sort(
      (a, b) =>
        new Date(a.lastTradeAt).getTime() - new Date(b.lastTradeAt).getTime()
    );
    let cumulative = 0;
    return sorted.map((pos) => {
      if (pos.pnl != null) cumulative += pos.pnl;
      return {
        date: new Date(pos.lastTradeAt).toLocaleDateString(),
        pnl: cumulative,
      };
    });
  }, [positions]);

  function handleSaveEditName(e: React.FormEvent) {
    e.preventDefault();
    const name = editNameValue.trim();
    if (!name || !profile) return;
    const updated: StoredProfile = { ...profile, displayName: name };
    localStorage.setItem(PROFILE_KEY, JSON.stringify(updated));
    saveProfile(updated);
    setEditingName(false);
    setEditNameValue("");
  }

  if (!profile) {
    return (
      <div className="p-4 md:p-6 max-w-md">
        <div className="bg-card rounded-lg border border-border p-6">
          <p className="text-muted-foreground">
            Enter your name in the pop-up to view your trades and PnL.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 max-w-4xl">
      <div className="mb-6">
        <Link
          to="/"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Home
        </Link>
      </div>

      <div className="bg-card rounded-lg border border-border p-6 mb-6">
        {editingName ? (
          <form onSubmit={handleSaveEditName} className="flex items-center gap-2">
            <Input
              type="text"
              value={editNameValue}
              onChange={(e) => setEditNameValue(e.target.value)}
              placeholder="Display name"
              className="max-w-xs"
            />
            <Button type="submit" size="sm">Save</Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setEditingName(false);
                setEditNameValue("");
              }}
            >
              Cancel
            </Button>
          </form>
        ) : (
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold text-foreground">
              {profile.displayName}
            </h1>
            <Button
              variant="ghost"
              size="sm"
              className="text-muted-foreground"
              onClick={() => {
                setEditNameValue(profile.displayName);
                setEditingName(true);
              }}
            >
              Change name
            </Button>
          </div>
        )}
      </div>

      <div className="bg-card rounded-lg border border-border p-6 mb-6">
        <h2 className="text-lg font-medium text-foreground mb-2">Balance</h2>
        <p className="text-2xl font-semibold text-primary">
          ${balance != null ? balance.toFixed(2) : "—"}
        </p>
        <p className="text-sm text-muted-foreground mt-1">
          Available for trading
        </p>
      </div>

      <div className="bg-card rounded-lg border border-border p-6 mb-6">
        <h2 className="text-lg font-medium text-foreground mb-2">Total PnL</h2>
        <p
          className={`text-2xl font-semibold ${
            totalPnl >= 0 ? "text-success" : "text-destructive"
          }`}
        >
          {totalPnl >= 0 ? "+" : ""}
          {totalPnl}
        </p>
      </div>

      {pnlChartData.length > 0 && (
        <div className="bg-card rounded-lg border border-border p-6 mb-6">
          <h2 className="text-lg font-medium text-foreground mb-4">
            PnL over time
          </h2>
          <div className="h-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={pnlChartData}>
                <XAxis
                  dataKey="date"
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
                  dataKey="pnl"
                  stroke="var(--primary)"
                  strokeWidth={2}
                  dot={true}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="bg-card rounded-lg border border-border p-6">
        <h2 className="text-lg font-medium text-foreground mb-4">Positions</h2>
        {loading ? (
          <p className="text-muted-foreground">Loading…</p>
        ) : positions.length === 0 ? (
          <p className="text-muted-foreground">No positions yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="pb-2 pr-4">Event</th>
                  <th className="pb-2 pr-4">Position</th>
                  <th className="pb-2 pr-4">Date</th>
                  <th className="pb-2 pr-4">Outcome</th>
                  <th className="pb-2">PnL</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos) => (
                  <tr
                    key={pos.eventId}
                    className="border-b border-border/50"
                  >
                    <td className="py-2 pr-4">
                      <Link
                        to={`/events/${pos.eventId}`}
                        className="text-primary hover:underline"
                      >
                        {pos.eventName}
                      </Link>
                    </td>
                    <td className="py-2 pr-4">
                      {pos.netSize === 0
                        ? "Closed"
                        : `${pos.netSize} ${pos.netSide === "up" ? "Up" : "Down"}`}
                    </td>
                    <td className="py-2 pr-4">
                      {new Date(pos.lastTradeAt).toLocaleString()}
                    </td>
                    <td className="py-2 pr-4">
                      <span
                        className={
                          pos.outcome === "Won"
                            ? "text-success"
                            : pos.outcome === "Lost"
                              ? "text-destructive"
                              : pos.outcome === "Closed"
                                ? "text-muted-foreground"
                                : "text-muted-foreground"
                        }
                      >
                        {pos.outcome}
                      </span>
                    </td>
                    <td className="py-2">
                      {pos.pnl != null ? (
                        <span
                          className={
                            pos.pnl >= 0
                              ? "text-success"
                              : "text-destructive"
                          }
                        >
                          {pos.pnl >= 0 ? "+" : ""}
                          {pos.pnl}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
