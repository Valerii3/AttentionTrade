import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

export interface AttentionEventCardData {
  eventId?: string;
  name: string;
  status: string;
  priceUp: number;
  priceDown: number;
  resolution: "up" | "down" | null;
  indexCurrent?: number;
  volume?: string;
  isDemo?: boolean;
}

interface AttentionEventCardProps {
  market: AttentionEventCardData;
}

export function AttentionEventCard({ market }: AttentionEventCardProps) {
  const upPct = Math.round(market.priceUp * 100);
  const downPct = Math.round(market.priceDown * 100);
  const isOpen = market.status === "open";
  const content = (
    <div className="bg-card rounded-lg border border-border p-4 hover:border-muted-foreground/50 transition-colors relative h-full flex flex-col">
      {market.isDemo && (
        <span className="absolute top-3 right-3 text-xs font-medium px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border">
          #demo
        </span>
      )}
      <h3 className="text-sm font-medium text-foreground leading-tight flex-1 pr-16">
        {market.name}
      </h3>
      <div className="space-y-2 mt-4">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Attention ↑</span>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-foreground">{upPct}%</span>
            {isOpen && (
              <div className="flex gap-1">
                <span className="px-2 py-0.5 text-xs font-medium rounded bg-success/20 text-success">
                  Yes
                </span>
                <span className="px-2 py-0.5 text-xs font-medium rounded bg-destructive/20 text-destructive">
                  No
                </span>
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Attention ↓</span>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-foreground">{downPct}%</span>
            {isOpen && (
              <div className="flex gap-1">
                <span className="px-2 py-0.5 text-xs font-medium rounded bg-success/20 text-success">
                  Yes
                </span>
                <span className="px-2 py-0.5 text-xs font-medium rounded bg-destructive/20 text-destructive">
                  No
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground mt-4 pt-3 border-t border-border">
        <span>{market.volume ?? "—"} Vol.</span>
        <span className="capitalize">{market.status}</span>
      </div>
    </div>
  );

  if (market.eventId && !market.isDemo) {
    return (
      <Link to={`/events/${market.eventId}`} className="block h-full">
        {content}
      </Link>
    );
  }

  return content;
}

export function PlaceholderCard() {
  return (
    <div
      className={cn(
        "bg-card rounded-lg border border-border p-8 flex flex-col items-center justify-center text-center",
        "text-muted-foreground text-sm min-h-[180px]"
      )}
    >
      <p>Coming soon</p>
    </div>
  );
}
