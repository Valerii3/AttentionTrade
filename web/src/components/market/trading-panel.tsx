import { useState, useRef, useEffect } from "react";
import { Info } from "lucide-react";
import { Button } from "@/components/ui/button";

interface TradingPanelProps {
  priceUp: number;
  priceDown: number;
  labelUp?: string | null;
  labelDown?: string | null;
  disabled?: boolean;
  onTrade: (side: "up" | "down", amount: number) => Promise<void>;
  error?: string;
  /** User's position on this event: total amount on up, total amount on down */
  positionUp?: number;
  positionDown?: number;
}

export function TradingPanel({
  priceUp,
  priceDown,
  labelUp = "Heating up",
  labelDown = "Cooling down",
  disabled,
  onTrade,
  error,
  positionUp = 0,
  positionDown = 0,
}: TradingPanelProps) {
  const [selectedOutcome, setSelectedOutcome] = useState<"up" | "down">("up");
  const [amount, setAmount] = useState(5);
  const [trading, setTrading] = useState(false);
  const [closing, setClosing] = useState(false);
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);
  const closeDialogRef = useRef<HTMLDialogElement>(null);

  const selectedPrice = selectedOutcome === "up" ? priceUp : priceDown;
  const potentialWin = amount / selectedPrice;

  const hasPosition = positionUp > 0 || positionDown > 0;
  const closeAmount = Math.abs(positionUp - positionDown);
  const closeSide: "up" | "down" = positionUp >= positionDown ? "down" : "up";
  const positionLabel = positionUp >= positionDown ? labelUp : labelDown;

  // For the close dialog: sell price = current market price of the side they're long
  const currentSellPrice = closeSide === "down" ? priceUp : priceDown; // 0–1
  const totalInvested = closeAmount;
  const currentValue = totalInvested * currentSellPrice;
  const pnl = currentValue - totalInvested;
  const pnlPercent =
    totalInvested > 0 ? (pnl / totalInvested) * 100 : 0;
  const isProfit = pnl >= 0;

  useEffect(() => {
    const dialog = closeDialogRef.current;
    if (!dialog) return;
    if (showCloseConfirm) dialog.showModal();
    else dialog.close();
  }, [showCloseConfirm]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setTrading(true);
    try {
      await onTrade(selectedOutcome, amount);
    } finally {
      setTrading(false);
    }
  }

  async function handleClosePosition() {
    if (!hasPosition || closeAmount <= 0) return;
    setClosing(true);
    setShowCloseConfirm(false);
    try {
      await onTrade(closeSide, closeAmount);
    } finally {
      setClosing(false);
    }
  }

  function openCloseConfirm() {
    if (!hasPosition || closing) return;
    setShowCloseConfirm(true);
  }

  return (
    <div className="bg-card border border-border rounded-lg p-4 w-full max-w-sm font-sans antialiased">
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <span className="text-sm font-medium text-foreground border-b-2 border-foreground pb-1">
            Buy
          </span>
        </div>

        {/* Outcome buttons */}
        <div className="flex gap-2 mb-6">
          <button
            type="button"
            onClick={() => setSelectedOutcome("up")}
            className={`flex-1 py-2.5 rounded-lg font-medium text-sm transition-colors ${
              selectedOutcome === "up"
                ? "bg-success text-success-foreground"
                : "bg-secondary text-muted-foreground hover:bg-secondary/80"
            }`}
          >
            {labelUp} {(priceUp * 100).toFixed(0)}¢
          </button>
          <button
            type="button"
            onClick={() => setSelectedOutcome("down")}
            className={`flex-1 py-2.5 rounded-lg font-medium text-sm transition-colors ${
              selectedOutcome === "down"
                ? "bg-success text-success-foreground"
                : "bg-secondary text-muted-foreground hover:bg-secondary/80"
            }`}
          >
            {labelDown} {(priceDown * 100).toFixed(0)}¢
          </button>
        </div>

        {/* Amount section - dollars */}
        <div className="mb-4">
          <div className="text-muted-foreground text-sm mb-2">Amount</div>
          <div className="text-foreground text-4xl font-bold text-right mb-3">
            ${amount}
          </div>
          <div className="flex gap-2 justify-end">
            {[1, 20, 100].map((val) => (
              <Button
                key={val}
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setAmount((a) => a + val)}
                className="bg-secondary border-border text-foreground text-xs px-3 h-8"
              >
                +${val}
              </Button>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="bg-secondary border-border text-foreground text-xs px-3 h-8"
            >
              Max
            </Button>
          </div>
        </div>

        {/* To win - leaf */}
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

        {/* Trade button - same colour as chart (primary) */}
        <Button
          type="submit"
          className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-medium py-6 text-lg"
          disabled={disabled || trading}
        >
          {trading ? "Trading…" : "Trade"}
        </Button>

        {/* Close position - distinct colour (amber) */}
        <Button
          type="button"
          variant="outline"
          className="w-full mt-3 border-amber-500/60 text-amber-600 hover:bg-amber-500/10 hover:border-amber-500/80 hover:text-amber-700 font-medium py-3 dark:text-amber-400 dark:hover:bg-amber-500/15 dark:hover:text-amber-300"
          disabled={!hasPosition || closing}
          onClick={openCloseConfirm}
        >
          {closing ? "Closing…" : "Close position"}
        </Button>

        {error && (
          <p className="text-sm text-destructive mt-2 text-center">{error}</p>
        )}
      </form>

      {/* Confirm close position dialog */}
      <dialog
        ref={closeDialogRef}
        onCancel={() => setShowCloseConfirm(false)}
        className="rounded-xl border border-border bg-card p-0 shadow-xl w-[min(100%,360px)] [&::backdrop]:bg-black/60 [&::backdrop]:backdrop-blur-sm"
      >
        <div className="p-6">
          <h3 className="text-lg font-semibold text-foreground mb-1">
            Close position
          </h3>
          <p className="text-sm text-muted-foreground mb-4">
            You’re closing ${closeAmount.toFixed(2)} on {positionLabel ?? (closeSide === "up" ? labelUp : labelDown)}.
          </p>

          <div className="rounded-lg border border-border bg-muted/30 p-4 space-y-3 mb-5">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Sell price</span>
              <span className="font-medium text-foreground">
                {(currentSellPrice * 100).toFixed(0)}¢
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Total invested</span>
              <span className="font-medium text-foreground">
                ${totalInvested.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Current value</span>
              <span className="font-medium text-foreground">
                ${currentValue.toFixed(2)}
              </span>
            </div>
            <div className="pt-2 border-t border-border flex justify-between items-center">
              <span className="text-sm font-medium text-foreground">
                P&L
              </span>
              <span
                className={
                  isProfit
                    ? "text-emerald-600 dark:text-emerald-400 font-bold text-base"
                    : "text-red-600 dark:text-red-400 font-bold text-base"
                }
              >
                {isProfit ? "+" : ""}
                {pnl.toFixed(2)} tokens ({isProfit ? "+" : ""}
                {pnlPercent.toFixed(1)}%)
              </span>
            </div>
          </div>

          <div className="flex gap-3 justify-end">
            <Button
              type="button"
              variant="outline"
              className="bg-secondary border-border"
              onClick={() => setShowCloseConfirm(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              className="bg-amber-500 text-white hover:bg-amber-600 border-0 disabled:opacity-50 disabled:pointer-events-none"
              onClick={handleClosePosition}
              disabled={totalInvested <= 0}
            >
              Confirm close
            </Button>
          </div>
        </div>
      </dialog>
    </div>
  );
}
