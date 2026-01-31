import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Canonical question text from topic and market type. */
export function formatCanonicalQuestion(
  topic: string,
  marketType: "1h" | "24h" = "1h"
): string {
  if (marketType === "24h") {
    return `Will attention around ${topic} remain elevated over the next 24 hours?`;
  }
  return `Will attention around ${topic} increase in the next 60 minutes?`;
}
