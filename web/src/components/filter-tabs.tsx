import { cn } from "@/lib/utils";

const filters = ["All", "Open", "Resolved"] as const;

export type FilterTab = (typeof filters)[number];

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
      </div>
    </div>
  );
}
