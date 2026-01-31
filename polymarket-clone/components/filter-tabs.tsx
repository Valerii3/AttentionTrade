"use client";

import { cn } from "@/lib/utils";
import { Search, SlidersHorizontal, Bookmark, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

const filters = [
  "All",
  "Gov Shutdown",
  "Grammys",
  "Seattle vs New England",
  "UFC 325",
  "Iran",
  "Trump",
  "Fed",
  "Minnesota Unrest",
  "Gold",
  "Silver",
  "Earnings",
  "Equities",
];

interface FilterTabsProps {
  selectedFilter: string;
  onFilterChange: (filter: string) => void;
}

export function FilterTabs({ selectedFilter, onFilterChange }: FilterTabsProps) {
  return (
    <div className="bg-background px-4 py-3">
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1 overflow-x-auto scrollbar-hide flex-1">
          {filters.map((filter) => {
            const isActive = selectedFilter === filter;
            return (
              <button
                key={filter}
                onClick={() => onFilterChange(filter)}
                className={cn(
                  "whitespace-nowrap px-3 py-1.5 text-sm font-medium rounded-full transition-colors border",
                  isActive
                    ? "text-primary border-primary bg-primary/10"
                    : "text-muted-foreground border-border hover:text-foreground hover:border-muted-foreground"
                )}
              >
                {filter}
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-1 border-l border-border pl-2">
          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
            <Search className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
            <SlidersHorizontal className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
            <Bookmark className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
