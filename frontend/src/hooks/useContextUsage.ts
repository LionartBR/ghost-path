/* useContextUsage — derives display values from ContextUsage. */

import type { ContextUsage } from "../types";

export function formatContextUsage(usage: ContextUsage | null) {
  if (!usage) return null;
  return {
    percentage: usage.usage_percentage,
    label: `${(usage.tokens_used / 1000).toFixed(0)}k / ${(usage.tokens_limit / 1000).toFixed(0)}k`,
    roundsLeft: usage.estimated_rounds_left,
    color:
      usage.usage_percentage > 80
        ? "red"
        : usage.usage_percentage > 50
          ? "yellow"
          : "green",
  };
}
