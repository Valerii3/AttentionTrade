import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";

interface CollapsibleSectionProps {
  title: string;
  defaultOpen?: boolean;
  action?: {
    label: string;
    onClick?: () => void;
    loading?: boolean;
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
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 bg-card hover:bg-secondary/50 transition-colors text-left"
      >
        <span className="text-foreground font-medium">{title}</span>
        <div className="flex items-center gap-2">
          {action && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                action.onClick?.();
              }}
              disabled={action.loading}
              className="text-primary hover:text-primary/80 text-sm h-auto py-1"
            >
              {action.loading ? "Generating…" : action.label}
            </Button>
          )}
          <ChevronDown
            className={`h-5 w-5 text-muted-foreground transition-transform shrink-0 ${
              isOpen ? "rotate-180" : ""
            }`}
          />
        </div>
      </button>
      {isOpen && children !== undefined && (
        <div className="p-4 bg-card border-t border-border">{children}</div>
      )}
    </div>
  );
}
