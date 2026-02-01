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
  /** Optional thumbnail URL for top-left of card. */
  imageUrl?: string | null;
}

interface AttentionEventCardProps {
  market: AttentionEventCardData;
  /** When set, show a delete button that calls this with eventId (no navigation on click). */
  onDelete?: (eventId: string) => void;
}

const DEFAULT_THUMBNAIL = "/event-thumbnail-placeholder.png";

export function AttentionEventCard({ market, onDelete }: AttentionEventCardProps) {
  const upPct = Math.round(market.priceUp * 100);
  const downPct = Math.round(market.priceDown * 100);
  const isOpen = market.status === "open";
  const thumbnailUrl = market.imageUrl || DEFAULT_THUMBNAIL;
  const handleDelete = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (market.eventId && onDelete) onDelete(market.eventId);
  };
  const content = (
    <div className="bg-card rounded-lg border border-border p-4 hover:border-muted-foreground/50 transition-colors relative h-full flex flex-col">
      <div className="absolute top-3 right-3 flex items-center gap-1">
        {market.eventId && onDelete && (
          <button
            type="button"
            onClick={handleDelete}
            className="text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded p-1.5 text-xs font-medium transition-colors"
            title="Delete event"
            aria-label="Delete event"
          >
            Delete
          </button>
        )}
        {(market.isDemo || market.demo) && (
          <span className="text-xs font-medium px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border" title="Demo markets use accelerated attention dynamics.">
            Demo
          </span>
        )}
      </div>
      <div className="flex gap-3 mb-2">
        <img
          src={thumbnailUrl}
          alt=""
          className="w-14 h-14 rounded-lg object-cover shrink-0 bg-muted"
        />
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-medium text-foreground leading-tight pr-8">
            {market.headline ?? (market.marketType ? formatCanonicalQuestion(market.name, market.marketType) : market.name)}
          </h3>
          {market.subline && (
            <p className="text-xs text-muted-foreground mt-0.5">{market.subline}</p>
          )}
        </div>
      </div>
      <div className="space-y-2 mt-2">
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
