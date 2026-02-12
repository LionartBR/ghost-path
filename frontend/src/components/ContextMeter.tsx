import type { ContextUsage } from "../types";
import { formatContextUsage } from "../hooks/useContextUsage";

interface Props {
  usage: ContextUsage | null;
}

export function ContextMeter({ usage }: Props) {
  const formatted = formatContextUsage(usage);
  if (!formatted) return null;

  const barColor =
    formatted.color === "red"
      ? "bg-red-500"
      : formatted.color === "yellow"
        ? "bg-yellow-500"
        : "bg-green-500";

  return (
    <div className="flex items-center gap-3 text-xs text-gray-500">
      <span>Context:</span>
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden max-w-[200px]">
        <div
          className={`h-full ${barColor} rounded-full transition-all`}
          style={{ width: `${Math.min(formatted.percentage, 100)}%` }}
        />
      </div>
      <span>{formatted.label}</span>
      <span className="text-gray-400">
        ~{formatted.roundsLeft} rounds left
      </span>
    </div>
  );
}
