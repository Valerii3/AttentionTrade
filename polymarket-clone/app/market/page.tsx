import { Header } from "@/components/header";
import { MarketHeader, MarketFilters } from "@/components/market/market-header";
import { PriceChart } from "@/components/market/price-chart";
import { TradingPanel } from "@/components/market/trading-panel";
import { OrderBook, MarketContext } from "@/components/market/collapsible-section";
import { RulesSection } from "@/components/market/rules-section";
import { CommentsSection } from "@/components/market/comments-section";

export default function MarketPage() {
  const marketRules = `This market will resolve to "Up" if the official S&P 500 Index open price for S&P 500 (SPX) on February 2 is higher than the previous trading day's closing price. The market will resolve to "Down" if the opening price is lower than or equal to the previous day's close. Resolution will be based on data from official market sources including NYSE and NASDAQ.`;

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex gap-6">
          {/* Left column - Main content */}
          <div className="flex-1 min-w-0">
            <MarketHeader
              badge="500"
              title="S&P 500 (SPX) Opens Up or Down on February 2?"
            />
            <MarketFilters />
            <PriceChart />
            
            {/* Collapsible sections */}
            <div className="mt-6 space-y-3">
              <OrderBook />
              <MarketContext />
            </div>
            
            <RulesSection rules={marketRules} />
            <CommentsSection />
          </div>
          
          {/* Right column - Trading panel */}
          <div className="hidden lg:block shrink-0">
            <div className="sticky top-6">
              <TradingPanel />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
