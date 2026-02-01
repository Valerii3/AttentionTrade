import { useState } from "react";

interface RulesSectionProps {
  rules: string;
}

export function RulesSection({ rules }: RulesSectionProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const truncatedRules =
    rules.length > 150 ? rules.slice(0, 150) + "..." : rules;

  return (
    <div className="mt-6">
      <h3 className="text-foreground font-semibold mb-3">Rules</h3>
      <p className="text-muted-foreground text-sm leading-relaxed">
        {isExpanded ? rules : truncatedRules}
        {rules.length > 150 && (
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-primary hover:underline ml-1"
          >
            {isExpanded ? "Show less" : "Show more"}
          </button>
        )}
      </p>
    </div>
  );
}
