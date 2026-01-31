import { Link } from "react-router-dom";
import { cn, formatCanonicalQuestion } from "@/lib/utils";

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
  /** When set, display canonical question from topic (name) + marketType. */
  marketType?: "1h" | "24h";
  /** True when event is a demo market (accelerated dynamics). */
  demo?: boolean;
  /** AI headline (e.g. "Is X gaining momentum?"). */
  headline?: string;
  /** Subline (e.g. "Attention change · next 60 min"). */
  subline?: string;
  /** Button label for up (e.g. "Heating up"). */
  labelUp?: string;
  /** Button label for down (e.g. "Cooling down"). */
  labelDown?: string;
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
      {(market.isDemo || market.demo) && (
        <span className="absolute top-3 right-3 text-xs font-medium px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border" title="Demo markets use accelerated attention dynamics.">
          Demo
        </span>
      )}
      <h3 className="text-sm font-medium text-foreground leading-tight flex-1 pr-16">
        {market.headline ?? (market.marketType ? formatCanonicalQuestion(market.name, market.marketType) : market.name)}
      </h3>
      {market.subline && (
        <p className="text-xs text-muted-foreground mt-0.5">{market.subline}</p>
      )}
      <div className="space-y-2 mt-4">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">{market.labelUp ?? "Heating up"}</span>
          <span className="text-sm font-medium text-foreground">{upPct}%</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">{market.labelDown ?? "Cooling down"}</span>
          <span className="text-sm font-medium text-foreground">{downPct}%</span>
        </div>
        {isOpen && (
          <div className="flex gap-2 mt-3">
            <span className="flex-1 px-3 py-2 text-center text-sm font-medium rounded bg-success/20 text-success border border-success/30">
              {market.labelUp ?? "Heating up"}
            </span>
            <span className="flex-1 px-3 py-2 text-center text-sm font-medium rounded bg-destructive/20 text-destructive border border-destructive/30">
              {market.labelDown ?? "Cooling down"}
            </span>
          </div>
        )}
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground mt-4 pt-3 border-t border-border">
        <span>{market.volume ?? "0"} Vol.</span>
        <span className="capitalize">{market.status}</span>
      </div>
    </div>
  );

  if (market.eventId) {
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
