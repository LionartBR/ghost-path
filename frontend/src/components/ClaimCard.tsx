import { useState } from "react";
import type { Claim } from "../types";

interface ClaimCardProps {
  claim: Claim;
  index: number;
}

export default function ClaimCard({ claim, index }: ClaimCardProps) {
  const [expanded, setExpanded] = useState(false);

  const confidenceBadge = {
    speculative: "bg-yellow-600 text-yellow-100",
    emerging: "bg-blue-600 text-blue-100",
    grounded: "bg-green-600 text-green-100",
  };

  const badgeColor = claim.confidence
    ? confidenceBadge[claim.confidence]
    : "bg-gray-600 text-gray-100";

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-gray-400 text-sm font-mono">#{index + 1}</span>
            {claim.confidence && (
              <span
                className={`px-2 py-1 rounded text-xs font-medium ${badgeColor}`}
              >
                {claim.confidence}
              </span>
            )}
          </div>
          <p className="text-white text-lg font-medium leading-relaxed">
            {claim.claim_text}
          </p>
        </div>
      </div>

      {claim.reasoning && (
        <div className="mt-4 p-3 bg-gray-900 rounded border border-gray-700">
          <p className="text-sm text-gray-400 font-semibold mb-1">Reasoning</p>
          <p className="text-gray-300 text-sm leading-relaxed">{claim.reasoning}</p>
        </div>
      )}

      {claim.falsifiability_condition && (
        <div className="mt-3 p-3 bg-gray-900 rounded border border-gray-700">
          <p className="text-sm text-gray-400 font-semibold mb-1">
            Falsifiability Condition
          </p>
          <p className="text-gray-300 text-sm leading-relaxed">
            {claim.falsifiability_condition}
          </p>
        </div>
      )}

      {claim.scores && (
        <div className="mt-4 grid grid-cols-2 gap-3">
          {Object.entries(claim.scores).map(([key, value]) =>
            value !== null ? (
              <div key={key}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-gray-400 capitalize">{key}</span>
                  <span className="text-xs text-gray-300 font-mono">
                    {value.toFixed(1)}
                  </span>
                </div>
                <div className="w-full bg-gray-700 rounded h-2">
                  <div
                    className="bg-blue-500 h-2 rounded"
                    style={{ width: `${value * 10}%` }}
                  />
                </div>
              </div>
            ) : null
          )}
        </div>
      )}

      {claim.evidence && claim.evidence.length > 0 && (
        <div className="mt-4">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-sm text-blue-400 hover:text-blue-300 font-medium mb-2"
          >
            {expanded ? "Hide" : "Show"} Evidence ({claim.evidence.length})
          </button>
          {expanded && (
            <div className="space-y-2">
              {claim.evidence.map((ev, i) => (
                <div
                  key={i}
                  className="p-3 bg-gray-900 rounded border border-gray-700"
                >
                  <a
                    href={ev.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:text-blue-300 text-sm font-medium"
                  >
                    {ev.title}
                  </a>
                  <p className="text-gray-400 text-xs mt-1">{ev.summary}</p>
                  {ev.type && (
                    <span className="inline-block mt-1 px-2 py-0.5 bg-gray-700 text-gray-300 text-xs rounded">
                      {ev.type}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {claim.score_reasoning && (
        <div className="mt-3 p-3 bg-gray-900 rounded border border-gray-700">
          <p className="text-sm text-gray-400 font-semibold mb-1">
            Score Reasoning
          </p>
          <p className="text-gray-300 text-sm leading-relaxed">
            {claim.score_reasoning}
          </p>
        </div>
      )}
    </div>
  );
}
