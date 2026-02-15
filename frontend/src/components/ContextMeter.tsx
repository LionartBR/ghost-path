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
  const u = usage ?? {
    tokens_used: 0,
    tokens_limit: 1_000_000,
    tokens_remaining: 1_000_000,
    usage_percentage: 0,
    input_tokens: 0,
    output_tokens: 0,
    cache_creation_tokens: 0,
    cache_read_tokens: 0,
  };

  const cacheTotal = (u.cache_creation_tokens ?? 0) + (u.cache_read_tokens ?? 0);
  const cacheRead = u.cache_read_tokens ?? 0;

  const inputTooltip = [
    `Input tokens (sent to model): ${u.input_tokens.toLocaleString()}`,
    cacheTotal > 0
      ? `Includes ${cacheTotal.toLocaleString()} cached tokens (${cacheRead.toLocaleString()} cache hits)`
      : null,
  ].filter(Boolean).join("\n");

  return (
    <span className="text-xs text-gray-400 font-mono tabular-nums inline-flex items-center gap-2">
      <span className="text-gray-500">tokens:</span>
      <span title={inputTooltip}>
        <span className="text-blue-400">↑</span> {formatNumber(u.input_tokens)}
      </span>
      <span title="Output tokens (received from model)">
        <span className="text-emerald-400">↓</span> {formatNumber(u.output_tokens)}
      </span>
      {cacheTotal > 0 && (
        <>
          <span className="text-gray-300">|</span>
          <span
            title={`Cache savings: ${cacheRead.toLocaleString()} tokens read from cache (0.1x cost)`}
            className="text-amber-400/80"
          >
            ⚡ {formatNumber(cacheRead)}
          </span>
        </>
      )}
      <span className="text-gray-300">|</span>
      <span title={`Total tokens: ${u.tokens_used.toLocaleString()} / ${u.tokens_limit.toLocaleString()}`}>
        {formatNumber(u.tokens_used)}
      </span>
    </span>
  );
};
