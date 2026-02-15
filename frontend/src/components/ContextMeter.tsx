import React from "react";
import type { ContextUsage } from "../types";

interface ContextMeterProps {
  usage: ContextUsage | null;
}

const formatNumber = (num: number): string => {
  if (num >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(2)}M`;
  }
  if (num >= 1_000) {
    return `${(num / 1_000).toFixed(1)}K`;
  }
  return num.toString();
};

export const ContextMeter: React.FC<ContextMeterProps> = ({ usage }) => {
  if (!usage || usage.tokens_used === 0) {
    return null;
  }

  return (
    <span className="text-xs text-gray-400 font-mono tabular-nums inline-flex items-center gap-2">
      <span title="Input tokens (sent to model)">
        <span className="text-blue-400">↑</span> {formatNumber(usage.input_tokens)}
      </span>
      <span title="Output tokens (received from model)">
        <span className="text-emerald-400">↓</span> {formatNumber(usage.output_tokens)}
      </span>
      <span className="text-gray-300">|</span>
      <span title="Total tokens used">{formatNumber(usage.tokens_used)}</span>
    </span>
  );
};
