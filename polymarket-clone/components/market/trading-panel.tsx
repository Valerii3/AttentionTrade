"use client";

import { useState } from "react";
import { ChevronDown, Info } from "lucide-react";
import { Button } from "@/components/ui/button";

export function TradingPanel() {
  const [activeTab, setActiveTab] = useState<"buy" | "sell">("buy");
  const [selectedOutcome, setSelectedOutcome] = useState<"up" | "down">("up");
  const [amount, setAmount] = useState(5);

  const upPrice = 0.27;
  const downPrice = 0.75;
  const selectedPrice = selectedOutcome === "up" ? upPrice : downPrice;
  const potentialWin = amount / selectedPrice;

  return (
    <div className="bg-card border border-border rounded-lg p-4 w-full max-w-sm">
      {/* Buy/Sell tabs */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-4">
          <button
            onClick={() => setActiveTab("buy")}
            className={`text-sm font-medium pb-1 ${
              activeTab === "buy"
                ? "text-foreground border-b-2 border-foreground"
                : "text-muted-foreground"
            }`}
          >
            Buy
          </button>
          <button
            onClick={() => setActiveTab("sell")}
            className={`text-sm font-medium pb-1 ${
              activeTab === "sell"
                ? "text-foreground border-b-2 border-foreground"
                : "text-muted-foreground"
            }`}
          >
            Sell
          </button>
        </div>
        <Button variant="ghost" size="sm" className="text-muted-foreground text-xs h-auto py-1">
          Market <ChevronDown className="h-3 w-3 ml-1" />
        </Button>
      </div>

      {/* Outcome buttons */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setSelectedOutcome("up")}
          className={`flex-1 py-2.5 rounded-lg font-medium text-sm transition-colors ${
            selectedOutcome === "up"
              ? "bg-success text-success-foreground"
              : "bg-secondary text-muted-foreground hover:bg-secondary/80"
          }`}
        >
          Up {(upPrice * 100).toFixed(0)}¢
        </button>
        <button
          onClick={() => setSelectedOutcome("down")}
          className={`flex-1 py-2.5 rounded-lg font-medium text-sm transition-colors ${
            selectedOutcome === "down"
              ? "bg-success text-success-foreground"
              : "bg-secondary text-muted-foreground hover:bg-secondary/80"
          }`}
        >
          Down {(downPrice * 100).toFixed(0)}¢
        </button>
      </div>

      {/* Amount section */}
      <div className="mb-4">
        <div className="text-muted-foreground text-sm mb-2">Amount</div>
        <div className="text-foreground text-4xl font-bold text-right mb-3">
          ${amount}
        </div>
        <div className="flex gap-2 justify-end">
          {[1, 20, 100].map((val) => (
            <Button
              key={val}
              variant="outline"
              size="sm"
              onClick={() => setAmount(amount + val)}
              className="bg-secondary border-border text-foreground text-xs px-3 h-8"
            >
              +${val}
            </Button>
          ))}
          <Button
            variant="outline"
            size="sm"
            className="bg-secondary border-border text-foreground text-xs px-3 h-8"
          >
            Max
          </Button>
        </div>
      </div>

      {/* To win section */}
      <div className="mb-4">
        <div className="flex items-center gap-2 text-muted-foreground text-sm mb-1">
          <span>To win</span>
          <span className="text-lg">🥬</span>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1 text-muted-foreground text-xs">
            Avg. Price {(selectedPrice * 100).toFixed(0)}¢
            <Info className="h-3 w-3" />
          </div>
          <div className="text-success text-3xl font-bold">
            ${potentialWin.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Trade button */}
      <Button className="w-full bg-primary/60 hover:bg-primary/70 text-foreground font-medium py-6 text-lg">
        Trade
      </Button>

      {/* Terms */}
      <p className="text-muted-foreground text-xs text-center mt-3">
        By trading, you agree to the{" "}
        <a href="#" className="text-primary hover:underline">
          Terms of Use
        </a>
        .
      </p>
    </div>
  );
}
