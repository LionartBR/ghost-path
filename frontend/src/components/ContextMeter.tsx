import React from "react";
import { useTranslation } from "react-i18next";
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

const getBarColor = (percentage: number): string => {
  if (percentage >= 90) return "bg-red-500";
  if (percentage >= 70) return "bg-amber-500";
  if (percentage >= 50) return "bg-yellow-500";
  return "bg-teal-500";
};

export const ContextMeter: React.FC<ContextMeterProps> = ({ usage }) => {
  const { t } = useTranslation();

  if (!usage) {
    return (
      <div className="flex items-center gap-3">
        <span className="text-xs text-gray-400">{t("context.label")}</span>
        <div className="w-32 h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div className="h-full bg-gray-300 w-0" />
        </div>
        <span className="text-xs text-gray-400">--</span>
      </div>
    );
  }

  const { tokens_used, tokens_limit, usage_percentage } = usage;
  const barColor = getBarColor(usage_percentage);

  return (
    <div className="flex items-center gap-3">
      <div className="w-32 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${barColor} transition-all duration-500 ease-out rounded-full`}
          style={{ width: `${Math.min(usage_percentage, 100)}%` }}
        />
      </div>
      <span className="text-xs text-gray-500 font-medium tabular-nums">
        {formatNumber(tokens_used)} / {formatNumber(tokens_limit)}
      </span>
      {usage_percentage >= 90 && (
        <span className="text-xs text-red-600 font-medium">{t("context.approaching")}</span>
      )}
    </div>
  );
};
