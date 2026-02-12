import { useState } from "react";
import type { Premise } from "../types";
import { ScoreSlider } from "./ScoreSlider";

interface Props {
  premise: Premise;
  isStreaming: boolean;
  onScore: (score: number) => void;
  onComment: (comment: string) => void;
}

const TYPE_COLORS: Record<string, string> = {
  initial: "bg-blue-100 text-blue-800",
  conservative: "bg-green-100 text-green-800",
  radical: "bg-red-100 text-red-800",
  combination: "bg-purple-100 text-purple-800",
};

export function PremiseCard({
  premise,
  isStreaming,
  onScore,
  onComment,
}: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border-2 border-gray-200 rounded-xl p-5 space-y-3 bg-white">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-semibold text-gray-900 text-lg">
          {premise.title}
        </h3>
        <span
          className={`px-2 py-0.5 rounded-full text-xs font-medium shrink-0 ${TYPE_COLORS[premise.premise_type] || "bg-gray-100"}`}
        >
          {premise.premise_type}
        </span>
      </div>

      <p className="text-sm text-gray-600 leading-relaxed">
        {expanded ? premise.body : `${premise.body?.slice(0, 200)}...`}
      </p>
      {premise.body && premise.body.length > 200 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-blue-600 hover:underline"
        >
          {expanded ? "Show less" : "Read more"}
        </button>
      )}

      {premise.violated_axiom && (
        <p className="text-xs text-red-600">
          Violated axiom: {premise.violated_axiom}
        </p>
      )}
      {premise.cross_domain_source && (
        <p className="text-xs text-purple-600">
          Inspired by: {premise.cross_domain_source}
        </p>
      )}

      {!isStreaming && (
        <div className="pt-2 space-y-2 border-t border-gray-100">
          <ScoreSlider value={premise.score ?? undefined} onChange={onScore} />
          <input
            type="text"
            placeholder="Optional comment..."
            onChange={(e) => onComment(e.target.value)}
            className="w-full px-3 py-1.5 text-sm border border-gray-200
                       rounded-lg focus:ring-1 focus:ring-gray-400
                       focus:border-transparent"
          />
        </div>
      )}
    </div>
  );
}
