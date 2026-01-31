import { Trophy, TrendingUp, Zap, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

const categories = [
  { id: "hackathon", label: "Hackathon", icon: Trophy },
  { id: "trending", label: "Trending", icon: TrendingUp },
  { id: "breaking", label: "Breaking", icon: Zap },
  { id: "new", label: "New", icon: Sparkles },
  { id: "politics", label: "Politics" },
  { id: "sports", label: "Sports" },
  { id: "crypto", label: "Crypto" },
  { id: "finance", label: "Finance" },
  { id: "tech", label: "Tech" },
  { id: "culture", label: "Culture" },
  { id: "world", label: "World" },
  { id: "economy", label: "Economy" },
  { id: "climate", label: "Climate & Science" },
  { id: "elections", label: "Elections" },
];

interface CategoryNavProps {
  selectedCategory: string;
  onCategoryChange: (category: string) => void;
}

export function CategoryNav({
  selectedCategory,
  onCategoryChange,
}: CategoryNavProps) {
  return (
    <div className="border-b border-border bg-background">
      <div className="px-4 py-2">
        <div className="flex items-center gap-1 overflow-x-auto scrollbar-hide">
          {categories.map((category) => {
            const Icon = category.icon;
            const isActive = selectedCategory === category.id;
            return (
              <button
                key={category.id}
                onClick={() => onCategoryChange(category.id)}
                className={cn(
                  "flex items-center gap-1.5 whitespace-nowrap px-3 py-2 text-sm font-medium rounded-md transition-colors",
                  isActive
                    ? "text-foreground bg-secondary"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                )}
              >
                {Icon && <Icon className="h-4 w-4" />}
                {category.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
