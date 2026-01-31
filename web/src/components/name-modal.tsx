import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { StoredProfile } from "@/lib/profile";

interface NameModalProps {
  onSubmit: (profile: StoredProfile) => void;
  onSkip?: () => void;
}

export function NameModal({ onSubmit, onSkip }: NameModalProps) {
  const [nameInput, setNameInput] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const name = nameInput.trim();
    if (!name) return;
    const traderId = crypto.randomUUID();
    onSubmit({ displayName: name, traderId });
    setNameInput("");
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="name-modal-title"
    >
      <div
        className="bg-card border border-border rounded-lg p-6 w-full max-w-md shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="name-modal-title" className="text-lg font-semibold text-foreground mb-2">
          Enter your name
        </h2>
        <p className="text-sm text-muted-foreground mb-4">
          Stored only on this device. No registration — just so we can track your trades.
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            type="text"
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
            placeholder="Display name"
            className="w-full"
            autoFocus
          />
          <div className="flex items-center gap-3">
            <Button type="submit" disabled={!nameInput.trim()}>
              Continue
            </Button>
            {onSkip && (
              <button
                type="button"
                onClick={onSkip}
                className="text-sm text-muted-foreground hover:text-foreground"
              >
                Skip for now
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
