import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { deleteEvent, listEvents, type Event } from "@/api-client/client";
import {
  AttentionEventCard,
  PlaceholderCard,
  type AttentionEventCardData,
} from "./market-card";

function formatVolume(v: number | undefined): string {
  if (v == null || v === 0) return "0";
  if (v >= 1000) return `${(v / 1000).toFixed(1)}k`;
  return String(Math.round(v));
}

function eventToCard(e: Event): AttentionEventCardData {
  return {
    eventId: e.id,
    name: e.name,
    status: e.status,
    priceUp: e.priceUp,
    priceDown: e.priceDown,
    resolution: e.resolution,
    indexCurrent: e.indexCurrent,
    volume: formatVolume(e.volume),
    isDemo: false,
    marketType: e.marketType ?? "1h",
    demo: e.demo,
    headline: e.headline ?? undefined,
    subline: e.subline ?? undefined,
    labelUp: e.labelUp ?? undefined,
    labelDown: e.labelDown ?? undefined,
    imageUrl: e.imageUrl ?? undefined,
  };
}

interface MarketGridProps {
  selectedCategory: string;
  selectedFilter: string;
}

export function MarketGrid({ selectedCategory, selectedFilter }: MarketGridProps) {
  const [searchParams] = useSearchParams();
  const q = searchParams.get("q")?.trim() ?? "";
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
        const params: { status?: "open" | "resolved"; q?: string } =
          status !== undefined ? { status } : {};
        if (q) params.q = q;
        const { events: list } = await listEvents(params);
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
  }, [selectedCategory, selectedFilter, q]);

  const handleDelete = useCallback(async (eventId: string) => {
    try {
      await deleteEvent(eventId);
      setEvents((prev) => prev.filter((e) => e.id !== eventId));
    } catch {
      // Refetch on error so list stays in sync
      const { events: list } = await listEvents({
        status: selectedFilter === "Open" ? "open" : selectedFilter === "Resolved" ? "resolved" : undefined,
        ...(q ? { q } : {}),
      });
      setEvents(list);
    }
  }, [selectedFilter, q]);

  if (selectedCategory !== "hackathon") {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4">
        <PlaceholderCard />
      </div>
    );
  }

  const cards = events.map(eventToCard);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4">
      {loading ? (
        <div className="col-span-full text-center py-12 text-muted-foreground">
          Loading…
        </div>
      ) : cards.length === 0 ? (
        <div className="col-span-full text-center py-12 text-muted-foreground">
          No markets yet. Create one to get started.
        </div>
      ) : (
        cards.map((market) => (
          <AttentionEventCard
            key={market.eventId}
            market={market}
            onDelete={handleDelete}
          />
        ))
      )}
    </div>
  );
}
