import { Share2, Bookmark } from "lucide-react";
import { Button } from "@/components/ui/button";

interface MarketHeaderProps {
  title: string;
  badge: string;
  badgeColor?: string;
}

export function MarketHeader({
  title,
  badge,
  badgeColor = "bg-primary/80",
}: MarketHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex items-center gap-3">
        <span
          className={`${badgeColor} text-primary-foreground font-bold px-2.5 py-1 rounded text-sm`}
        >
          {badge}
        </span>
        <h1 className="text-xl font-semibold text-foreground">{title}</h1>
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="text-muted-foreground hover:text-foreground"
        >
          <Share2 className="h-5 w-5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="text-muted-foreground hover:text-foreground"
        >
          <Bookmark className="h-5 w-5" />
        </Button>
      </div>
    </div>
  );
}

export interface MarketFiltersProps {
  windowEnd?: string;
  pastWindowsCount?: number;
}

export function MarketFilters({
  windowEnd,
  pastWindowsCount = 0,
}: MarketFiltersProps) {
  const dateLabel = windowEnd
    ? new Date(windowEnd).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      })
    : null;
  return (
    <div className="flex items-center gap-2 mt-4">
      <Button
        type="button"
        variant="outline"
        className="bg-secondary border-border text-foreground rounded-full px-4 py-1.5 h-auto text-sm"
      >
        Past{pastWindowsCount > 0 ? ` (${pastWindowsCount})` : ""}
      </Button>
      {dateLabel && (
        <Button
          type="button"
          variant="outline"
          className="bg-card border-border text-foreground rounded-full px-4 py-1.5 h-auto text-sm"
        >
          {dateLabel}
        </Button>
      )}
    </div>
  );
}
