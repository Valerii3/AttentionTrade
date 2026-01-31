"use client";

import { cn } from "@/lib/utils";
import { Gift, Bookmark } from "lucide-react";
import { Button } from "@/components/ui/button";
import Image from "next/image";

export type MarketType = "binary" | "versus" | "multi";

export interface MarketOption {
  name: string;
  odds: number;
  image?: string;
}

export interface Market {
  id: string;
  title: string;
  type: MarketType;
  options: MarketOption[];
  volume: string;
  category?: string;
  eventTime?: string;
  isLive?: boolean;
  gameInfo?: string;
  image?: string;
}

interface MarketCardProps {
  market: Market;
}

export function MarketCard({ market }: MarketCardProps) {
  if (market.type === "binary") {
    return <BinaryMarketCard market={market} />;
  }
  if (market.type === "versus") {
    return <VersusMarketCard market={market} />;
  }
  return <MultiMarketCard market={market} />;
}

function BinaryMarketCard({ market }: MarketCardProps) {
  return (
    <div className="bg-card rounded-lg border border-border p-4 hover:border-muted-foreground/50 transition-colors">
      <div className="flex items-start gap-3 mb-4">
        {market.image && (
          <div className="relative h-10 w-10 rounded-lg overflow-hidden flex-shrink-0">
            <Image src={market.image || "/placeholder.svg"} alt="" fill className="object-cover" />
          </div>
        )}
        <h3 className="text-sm font-medium text-foreground leading-tight flex-1">{market.title}</h3>
      </div>
      <div className="space-y-2 mb-4">
        {market.options.map((option) => (
          <div key={option.name} className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">{option.name}</span>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-foreground">{option.odds}%</span>
              <div className="flex gap-1">
                <button className="px-2 py-0.5 text-xs font-medium rounded bg-success/20 text-success hover:bg-success/30 transition-colors">
                  Yes
                </button>
                <button className="px-2 py-0.5 text-xs font-medium rounded bg-destructive/20 text-destructive hover:bg-destructive/30 transition-colors">
                  No
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{market.volume} Vol.</span>
        <div className="flex items-center gap-2">
          <button className="hover:text-foreground transition-colors">
            <Gift className="h-4 w-4" />
          </button>
          <button className="hover:text-foreground transition-colors">
            <Bookmark className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

function VersusMarketCard({ market }: MarketCardProps) {
  const [option1, option2] = market.options;
  return (
    <div className="bg-card rounded-lg border border-border p-4 hover:border-muted-foreground/50 transition-colors">
      <div className="space-y-3 mb-4">
        {market.options.map((option, index) => (
          <div key={option.name} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {option.image && (
                <div className="relative h-6 w-6 rounded-full overflow-hidden">
                  <Image src={option.image || "/placeholder.svg"} alt="" fill className="object-cover" />
                </div>
              )}
              <span className="text-sm font-medium text-foreground">{option.name}</span>
            </div>
            <span className="text-sm font-medium text-foreground">{option.odds}%</span>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2 mb-4">
        <Button
          variant="outline"
          className="bg-primary/10 border-primary/30 text-primary hover:bg-primary/20 font-medium"
        >
          {option1?.name}
        </Button>
        <Button
          variant="outline"
          className="bg-destructive/10 border-destructive/30 text-destructive hover:bg-destructive/20 font-medium"
        >
          {option2?.name}
        </Button>
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <span>{market.volume} Vol.</span>
          {market.category && (
            <>
              <span>·</span>
              <span>{market.category}</span>
            </>
          )}
          {market.eventTime && (
            <>
              <span>·</span>
              <span>{market.eventTime}</span>
            </>
          )}
        </div>
        <button className="hover:text-foreground transition-colors">
          <Bookmark className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function MultiMarketCard({ market }: MarketCardProps) {
  const hasThreeOptions = market.options.length === 3;
  return (
    <div className="bg-card rounded-lg border border-border p-4 hover:border-muted-foreground/50 transition-colors">
      <div className="flex items-start gap-3 mb-4">
        {market.image && (
          <div className="relative h-10 w-10 rounded-lg overflow-hidden flex-shrink-0">
            <Image src={market.image || "/placeholder.svg"} alt="" fill className="object-cover" />
          </div>
        )}
        <h3 className="text-sm font-medium text-foreground leading-tight flex-1">{market.title}</h3>
      </div>
      <div className="space-y-2 mb-4">
        {market.options.slice(0, 2).map((option) => (
          <div key={option.name} className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground truncate max-w-[60%]">{option.name}</span>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-foreground">{option.odds}%</span>
              <div className="flex gap-1">
                <button className="px-2 py-0.5 text-xs font-medium rounded bg-success/20 text-success hover:bg-success/30 transition-colors">
                  Yes
                </button>
                <button className="px-2 py-0.5 text-xs font-medium rounded bg-destructive/20 text-destructive hover:bg-destructive/30 transition-colors">
                  No
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <span>{market.volume} Vol.</span>
          {market.category && (
            <>
              <span>·</span>
              <span className="flex items-center gap-1">
                {market.isLive && <span className="w-1.5 h-1.5 rounded-full bg-destructive animate-pulse" />}
                {market.category}
              </span>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button className="hover:text-foreground transition-colors">
            <Gift className="h-4 w-4" />
          </button>
          <button className="hover:text-foreground transition-colors">
            <Bookmark className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

export function SportsMarketCard({ market }: MarketCardProps) {
  const [team1, team2] = market.options;
  const hasThreeOptions = market.options.length === 3;
  
  return (
    <div className="bg-card rounded-lg border border-border p-4 hover:border-muted-foreground/50 transition-colors">
      <div className="space-y-3 mb-4">
        {market.options.slice(0, 2).map((option, index) => (
          <div key={option.name} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {option.image ? (
                <div className="relative h-6 w-6 rounded overflow-hidden">
                  <Image src={option.image || "/placeholder.svg"} alt="" fill className="object-cover" />
                </div>
              ) : (
                <div className="h-6 w-6 rounded bg-muted flex items-center justify-center text-xs font-bold text-muted-foreground">
                  {index === 0 ? market.gameInfo?.split(" ")[0] || "1" : "0"}
                </div>
              )}
              <span className="text-sm font-medium text-foreground">{option.name}</span>
            </div>
            <span className="text-sm font-medium text-foreground">{option.odds}%</span>
          </div>
        ))}
      </div>
      <div className={cn("grid gap-2 mb-4", hasThreeOptions ? "grid-cols-3" : "grid-cols-2")}>
        <Button
          variant="outline"
          className="bg-primary/10 border-primary/30 text-primary hover:bg-primary/20 font-medium text-sm"
        >
          {team1?.name}
        </Button>
        {hasThreeOptions && (
          <Button
            variant="outline"
            className="bg-secondary border-border text-muted-foreground hover:bg-secondary/80 font-medium text-sm"
          >
            DRAW
          </Button>
        )}
        <Button
          variant="outline"
          className="bg-destructive/10 border-destructive/30 text-destructive hover:bg-destructive/20 font-medium text-sm"
        >
          {team2?.name}
        </Button>
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          {market.isLive && <span className="w-1.5 h-1.5 rounded-full bg-destructive animate-pulse" />}
          {market.gameInfo && <span>{market.gameInfo}</span>}
          <span>{market.volume} Vol.</span>
          {market.category && (
            <>
              <span>·</span>
              <span>{market.category}</span>
            </>
          )}
        </div>
        <button className="hover:text-foreground transition-colors">
          <Bookmark className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
