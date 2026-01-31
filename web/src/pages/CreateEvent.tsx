import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { proposeEvent } from "@/api-client/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function CreateEvent() {
  const [name, setName] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [description, setDescription] = useState("");
  const [marketType, setMarketType] = useState<"1h" | "24h">("1h");
  const [demo, setDemo] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successModal, setSuccessModal] = useState(false);
  const [acceptedEventId, setAcceptedEventId] = useState<string | null>(null);
  const [rejectionModal, setRejectionModal] = useState(false);
  const [rejectedMessage, setRejectedMessage] = useState<string | null>(null);

  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setRejectedMessage(null);
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    setLoading(true);
    try {
      const event = await proposeEvent(name.trim(), {
        sourceUrl: sourceUrl.trim() || undefined,
        description: description.trim() || undefined,
        marketType,
        demo,
      });
      if (event.status === "open") {
        setAcceptedEventId(event.id);
        setSuccessModal(true);
      } else if (event.status === "rejected") {
        setRejectedMessage(
          event.rejectReason ??
            "This event is not accepted for trading."
        );
        setRejectionModal(true);
      } else {
        setRejectedMessage(
          event.rejectReason ??
            "This event is not accepted for trading."
        );
        setRejectionModal(true);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to propose event"
      );
    } finally {
      setLoading(false);
    }
  }

  function closeSuccessModal() {
    setSuccessModal(false);
    if (acceptedEventId) {
      navigate(`/events/${acceptedEventId}`);
      setAcceptedEventId(null);
    }
  }

  function closeRejectionModal() {
    setRejectionModal(false);
    setRejectedMessage(null);
  }

  const modalBackdrop =
    "fixed inset-0 bg-black/60 flex items-center justify-center z-50";
  const modalPanel =
    "bg-card border border-border rounded-lg p-6 max-w-[320px] shadow-lg";

  return (
    <div className="p-4 md:p-6 max-w-lg">
      <h1 className="text-xl font-semibold text-foreground mb-6">
        Propose event
      </h1>

      {successModal && (
        <div
          className={modalBackdrop}
          onClick={closeSuccessModal}
          role="dialog"
          aria-modal="true"
        >
          <div
            className={modalPanel}
            onClick={(e) => e.stopPropagation()}
          >
            <p className="text-foreground mb-4">
              Event successfully created.
            </p>
            <Button onClick={closeSuccessModal}>OK</Button>
          </div>
        </div>
      )}

      {rejectionModal && (
        <div
          className={modalBackdrop}
          onClick={closeRejectionModal}
          role="dialog"
          aria-modal="true"
        >
          <div
            className={modalPanel}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-medium text-foreground mb-2">
              Event not tradable
            </h3>
            <p className="text-muted-foreground mb-4">
              {rejectedMessage ??
                "This event is not accepted for trading."}
            </p>
            <Button onClick={closeRejectionModal}>OK</Button>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-foreground mb-1.5">
            Topic or event
          </label>
          <p className="text-xs text-muted-foreground mb-1.5">
            The market will ask: Will attention around this increase in the next 60 minutes?
          </p>
          <Input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Cursor Hackathon Dec 24"
            className="w-full"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-1.5">
            Source URL (optional)
          </label>
          <Input
            type="url"
            value={sourceUrl}
            onChange={(e) => setSourceUrl(e.target.value)}
            placeholder="e.g. https://reddit.com/r/cursor/..."
            className="w-full"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-1.5">
            Description (optional)
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Short context if no URL"
            rows={2}
            className="flex min-h-[60px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>
        {showAdvanced && (
          <div className="space-y-2">
            <label className="block text-sm font-medium text-foreground">
              Market type
            </label>
            <div className="flex flex-col gap-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="marketType"
                  checked={marketType === "1h"}
                  onChange={() => setMarketType("1h")}
                  className="accent-primary"
                />
                <span className="text-sm">1h — Will attention increase in the next 60 minutes?</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="marketType"
                  checked={marketType === "24h"}
                  onChange={() => setMarketType("24h")}
                  className="accent-primary"
                />
                <span className="text-sm">24h — Will attention remain elevated over the next 24h?</span>
              </label>
            </div>
          </div>
        )}
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={demo}
            onChange={(e) => setDemo(e.target.checked)}
            className="accent-primary rounded"
          />
          <span className="text-sm text-muted-foreground">
            Create demo market (2-min window, accelerated attention dynamics)
          </span>
        </label>
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          {showAdvanced ? "Hide" : "Show"} advanced (24h market)
        </button>
        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}
        <Button type="submit" disabled={loading}>
          {loading
            ? "Proposing… Analyzing… Building index…"
            : "Propose"}
        </Button>
      </form>
    </div>
  );
}
