"use client";

import React from "react"

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";

interface CollapsibleSectionProps {
  title: string;
  defaultOpen?: boolean;
  action?: {
    label: string;
    onClick?: () => void;
  };
  children?: React.ReactNode;
}

export function CollapsibleSection({
  title,
  defaultOpen = false,
  action,
  children,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 bg-card hover:bg-secondary/50 transition-colors"
      >
        <span className="text-foreground font-medium">{title}</span>
        <div className="flex items-center gap-2">
          {action && (
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                action.onClick?.();
              }}
              className="text-primary hover:text-primary/80 text-sm h-auto py-1"
            >
              {action.label}
            </Button>
          )}
          <ChevronDown
            className={`h-5 w-5 text-muted-foreground transition-transform ${
              isOpen ? "rotate-180" : ""
            }`}
          />
        </div>
      </button>
      {isOpen && children && (
        <div className="p-4 bg-card border-t border-border">{children}</div>
      )}
    </div>
  );
}

export function OrderBook() {
  return (
    <CollapsibleSection title="Order Book">
      <div className="text-muted-foreground text-sm">
        Order book data will be displayed here.
      </div>
    </CollapsibleSection>
  );
}

export function MarketContext() {
  return (
    <CollapsibleSection title="Market Context" action={{ label: "Generate" }}>
      <div className="text-muted-foreground text-sm">
        AI-generated market context will appear here.
      </div>
    </CollapsibleSection>
  );
}
