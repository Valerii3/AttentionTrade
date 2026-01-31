import { useState } from "react";
import { CategoryNav } from "@/components/category-nav";
import { FilterTabs } from "@/components/filter-tabs";
import { MarketGrid } from "@/components/market-grid";

export default function Home() {
  const [selectedCategory, setSelectedCategory] = useState("hackathon");
  const [selectedFilter, setSelectedFilter] = useState("All");

  return (
    <main className="min-h-screen bg-background">
      <CategoryNav
        selectedCategory={selectedCategory}
        onCategoryChange={setSelectedCategory}
      />
      <FilterTabs
        selectedFilter={selectedFilter}
        onFilterChange={setSelectedFilter}
      />
      <MarketGrid
        selectedCategory={selectedCategory}
        selectedFilter={selectedFilter}
      />
    </main>
  );
}
