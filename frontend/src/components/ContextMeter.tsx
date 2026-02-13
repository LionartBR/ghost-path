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

const getColorClasses = (percentage: number): { bg: string; text: string } => {
  if (percentage >= 90) {
    return { bg: "bg-red-500", text: "text-red-400" };
  }
  if (percentage >= 70) {
    return { bg: "bg-orange-500", text: "text-orange-400" };
  }
  if (percentage >= 50) {
    return { bg: "bg-yellow-500", text: "text-yellow-400" };
  }
  return { bg: "bg-green-500", text: "text-green-400" };
};

export const ContextMeter: React.FC<ContextMeterProps> = ({ usage }) => {
  if (!usage) {
    return (
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-400">Context Usage</span>
          <span className="text-xs text-gray-500">No data</span>
        </div>
        <div className="w-full h-4 bg-gray-700 rounded-full overflow-hidden">
          <div className="h-full bg-gray-600 w-0" />
        </div>
      </div>
    );
  }

  const { tokens_used, tokens_limit, tokens_remaining, usage_percentage } = usage;
  const colors = getColorClasses(usage_percentage);

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-white">Context Usage</span>
        <span className={`text-sm font-bold ${colors.text}`}>
          {usage_percentage.toFixed(1)}%
        </span>
      </div>

      <div className="w-full h-4 bg-gray-700 rounded-full overflow-hidden mb-2">
        <div
          className={`h-full ${colors.bg} transition-all duration-500 ease-out`}
          style={{ width: `${Math.min(usage_percentage, 100)}%` }}
        />
      </div>

      <div className="flex items-center justify-between text-xs text-gray-400">
        <span>
          {formatNumber(tokens_used)} / {formatNumber(tokens_limit)}
        </span>
        <span>{formatNumber(tokens_remaining)} remaining</span>
      </div>

      {usage_percentage >= 90 && (
        <div className="mt-3 p-2 bg-red-900/30 border border-red-700 rounded">
          <p className="text-xs text-red-300 flex items-center gap-2">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            Context limit approaching - consider resolving soon
          </p>
        </div>
      )}
    </div>
  );
};
