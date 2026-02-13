import { useState } from "react";
import type { Claim } from "../types";

interface ClaimCardProps {
  claim: Claim;
  index: number;
}

const CLAIM_TYPE_BORDER: Record<string, string> = {
  thesis: "border-l-indigo-500",
  antithesis: "border-l-rose-500",
  synthesis: "border-l-teal-500",
  user_contributed: "border-l-purple-500",
  merged: "border-l-blue-500",
};

const CLAIM_TYPE_LABEL: Record<string, { text: string; color: string }> = {
  thesis: { text: "Thesis", color: "text-indigo-600" },
  antithesis: { text: "Antithesis", color: "text-rose-600" },
  synthesis: { text: "Synthesis", color: "text-teal-600" },
  user_contributed: { text: "User Contributed", color: "text-purple-600" },
  merged: { text: "Merged", color: "text-blue-600" },
};

const CONFIDENCE_BADGE: Record<string, string> = {
  speculative: "bg-amber-50 text-amber-700 border border-amber-200",
  emerging: "bg-yellow-50 text-yellow-700 border border-yellow-200",
  grounded: "bg-green-50 text-green-700 border border-green-200",
};

const SCORE_COLORS: Record<string, string> = {
  novelty: "bg-indigo-500",
  groundedness: "bg-teal-500",
  falsifiability: "bg-amber-500",
  significance: "bg-rose-500",
};

export default function ClaimCard({ claim, index }: ClaimCardProps) {
  const [expanded, setExpanded] = useState(false);

  const borderColor = claim.claim_type
    ? CLAIM_TYPE_BORDER[claim.claim_type] || "border-l-gray-300"
    : "border-l-gray-300";

  const typeLabel = claim.claim_type
    ? CLAIM_TYPE_LABEL[claim.claim_type]
    : null;

  const badgeClasses = claim.confidence
    ? CONFIDENCE_BADGE[claim.confidence] || "bg-gray-50 text-gray-600 border border-gray-200"
    : null;

  return (
    <div className={`bg-white border border-gray-200 rounded-lg shadow-sm border-l-4 ${borderColor}`}>
      <div className="p-5">
        {/* Header */}
        <div className="flex items-center gap-3 mb-3">
          {typeLabel && (
            <span className={`text-xs font-semibold uppercase tracking-wide ${typeLabel.color}`}>
              {typeLabel.text}
            </span>
          )}
          {!typeLabel && (
            <span className="text-xs text-gray-400 font-mono">#{index + 1}</span>
          )}
          {claim.confidence && badgeClasses && (
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${badgeClasses}`}>
              {claim.confidence}
            </span>
          )}
        </div>

        {/* Claim text */}
        <p className="text-gray-900 text-base font-medium leading-relaxed">
          {claim.claim_text}
        </p>

        {/* Reasoning */}
        {claim.reasoning && (
          <div className="mt-3 p-3 bg-gray-50 rounded-md border border-gray-100">
            <p className="text-xs text-gray-500 font-semibold mb-1 uppercase tracking-wide">Reasoning</p>
            <p className="text-gray-600 text-sm leading-relaxed">{claim.reasoning}</p>
          </div>
        )}

        {/* Falsifiability */}
        {claim.falsifiability_condition && (
          <div className="mt-3 p-3 bg-gray-50 rounded-md border border-gray-100">
            <p className="text-xs text-gray-500 font-semibold mb-1 uppercase tracking-wide">Falsifiability Condition</p>
            <p className="text-gray-600 text-sm leading-relaxed">{claim.falsifiability_condition}</p>
          </div>
        )}

        {/* Scores */}
        {claim.scores && (
          <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3">
            {Object.entries(claim.scores).map(([key, value]) =>
              value !== null ? (
                <div key={key}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-500 capitalize">{key}</span>
                    <span className="text-xs text-gray-700 font-semibold tabular-nums">
                      {Math.round(value * 10)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-1.5">
                    <div
                      className={`${SCORE_COLORS[key] || "bg-indigo-500"} h-1.5 rounded-full transition-all duration-300`}
                      style={{ width: `${value * 10}%` }}
                    />
                  </div>
                </div>
              ) : null
            )}
          </div>
        )}

        {/* Evidence toggle */}
        {claim.evidence && claim.evidence.length > 0 && (
          <div className="mt-4">
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-sm text-indigo-600 hover:text-indigo-500 font-medium"
            >
              {expanded ? "Hide" : "Show"} Evidence ({claim.evidence.length})
            </button>
            {expanded && (
              <div className="mt-2 space-y-2">
                {claim.evidence.map((ev, i) => (
                  <div key={i} className="p-3 bg-gray-50 rounded-md border border-gray-100">
                    <a
                      href={ev.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-600 hover:text-indigo-500 text-sm font-medium"
                    >
                      {ev.title}
                    </a>
                    <p className="text-gray-500 text-xs mt-1">{ev.summary}</p>
                    {ev.type && (
                      <span className="inline-block mt-1.5 px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded border border-gray-200">
                        {ev.type}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Score reasoning */}
        {claim.score_reasoning && (
          <div className="mt-3 p-3 bg-gray-50 rounded-md border border-gray-100">
            <p className="text-xs text-gray-500 font-semibold mb-1 uppercase tracking-wide">Score Reasoning</p>
            <p className="text-gray-600 text-sm leading-relaxed">{claim.score_reasoning}</p>
          </div>
        )}
      </div>
    </div>
  );
}
