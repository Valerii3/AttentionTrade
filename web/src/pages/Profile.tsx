import { useEffect, useState, useMemo } from "react";
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

function tradePnl(t: ProfileTrade): number | null {
  if (t.status !== "resolved" || t.resolution == null) return null;
  return t.resolution === t.side ? t.amount : -t.amount;
}

function tradeOutcome(t: ProfileTrade): "Won" | "Lost" | "Open" {
  if (t.status !== "resolved" || t.resolution == null) return "Open";
  return t.resolution === t.side ? "Won" : "Lost";
}

export default function Profile() {
  const { profile, saveProfile } = useProfile();
  const [trades, setTrades] = useState<ProfileTrade[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [editNameValue, setEditNameValue] = useState("");

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

  const totalPnl = useMemo(() => {
    return trades.reduce((sum, t) => {
      const p = tradePnl(t);
      return sum + (p ?? 0);
    }, 0);
  }, [trades]);

  const pnlChartData = useMemo(() => {
    const sorted = [...trades].sort(
      (a, b) =>
        new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
    );
    let cumulative = 0;
    return sorted.map((t) => {
      const p = tradePnl(t);
      if (p != null) cumulative += p;
      return {
        date: new Date(t.createdAt).toLocaleDateString(),
        pnl: cumulative,
      };
    });
  }, [trades]);

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
        <h2 className="text-lg font-medium text-foreground mb-4">Trades</h2>
        {loading ? (
          <p className="text-muted-foreground">Loading…</p>
        ) : trades.length === 0 ? (
          <p className="text-muted-foreground">No trades yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="pb-2 pr-4">Event</th>
                  <th className="pb-2 pr-4">Side</th>
                  <th className="pb-2 pr-4">Amount</th>
                  <th className="pb-2 pr-4">Date</th>
                  <th className="pb-2">Outcome</th>
                </tr>
              </thead>
              <tbody>
                {[...trades].reverse().map((t) => {
                  const outcome = tradeOutcome(t);
                  return (
                    <tr key={`${t.eventId}-${t.createdAt}`} className="border-b border-border/50">
                      <td className="py-2 pr-4">
                        <Link
                          to={`/events/${t.eventId}`}
                          className="text-primary hover:underline"
                        >
                          {t.eventName}
                        </Link>
                      </td>
                      <td className="py-2 pr-4">
                        {t.side === "up" ? "Up" : "Down"}
                      </td>
                      <td className="py-2 pr-4">{t.amount}</td>
                      <td className="py-2 pr-4">
                        {new Date(t.createdAt).toLocaleString()}
                      </td>
                      <td className="py-2">
                        <span
                          className={
                            outcome === "Won"
                              ? "text-success"
                              : outcome === "Lost"
                                ? "text-destructive"
                                : "text-muted-foreground"
                          }
                        >
                          {outcome}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
