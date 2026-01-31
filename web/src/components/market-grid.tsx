import { useEffect, useState } from "react";
import { listEvents, type Event } from "@/api-client/client";
import {
  AttentionEventCard,
  PlaceholderCard,
  type AttentionEventCardData,
} from "./market-card";

const DEMO_MARKETS: AttentionEventCardData[] = [
  {
    name: "Will 'Attention Economy' trend on Twitter this week?",
    status: "open",
    priceUp: 0.52,
    priceDown: 0.48,
    resolution: null,
    volume: "—",
    isDemo: true,
  },
  {
    name: "Will this repo get 100 GitHub stars by Friday?",
    status: "open",
    priceUp: 0.38,
    priceDown: 0.62,
    resolution: null,
    volume: "—",
    isDemo: true,
  },
  {
    name: "Will AI headlines dominate front page tomorrow?",
    status: "open",
    priceUp: 0.71,
    priceDown: 0.29,
    resolution: null,
    volume: "—",
    isDemo: true,
  },
];

function eventToCard(e: Event): AttentionEventCardData {
  return {
    eventId: e.id,
    name: e.name,
    status: e.status,
    priceUp: e.priceUp,
    priceDown: e.priceDown,
    resolution: e.resolution,
    indexCurrent: e.indexCurrent,
    volume: "—",
    isDemo: false,
  };
}

interface MarketGridProps {
  selectedCategory: string;
  selectedFilter: string;
}

export function MarketGrid({ selectedCategory, selectedFilter }: MarketGridProps) {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (selectedCategory !== "hackathon") {
      setEvents([]);
      setLoading(false);
      return;
    }
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const status =
          selectedFilter === "Open"
            ? "open"
            : selectedFilter === "Resolved"
              ? "resolved"
              : undefined;
        const { events: list } = await listEvents(status);
        if (!cancelled) setEvents(list);
      } catch {
        if (!cancelled) setEvents([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [selectedCategory, selectedFilter]);

  if (selectedCategory !== "hackathon") {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4">
        <PlaceholderCard />
      </div>
    );
  }

  const apiCards = events.map(eventToCard);
  const allCards = [...apiCards, ...DEMO_MARKETS];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4">
      {loading ? (
        <div className="col-span-full text-center py-12 text-muted-foreground">
          Loading…
        </div>
      ) : allCards.length === 0 ? (
        <div className="col-span-full text-center py-12 text-muted-foreground">
          No markets yet. Create one to get started.
        </div>
      ) : (
        allCards.map((market, i) => (
          <AttentionEventCard
            key={market.eventId ?? `demo-${i}`}
            market={market}
          />
        ))
      )}
    </div>
  );
}
