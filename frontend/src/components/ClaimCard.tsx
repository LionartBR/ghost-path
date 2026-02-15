import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { Claim } from "../types";

interface ClaimCardProps {
  claim: Claim;
  index: number;
  compact?: boolean;
}

const CLAIM_TYPE_BORDER: Record<string, string> = {
  thesis: "border-l-blue-500",
  antithesis: "border-l-blue-400",
  synthesis: "border-l-blue-600",
  user_contributed: "border-l-blue-500",
  merged: "border-l-blue-500",
};

const CLAIM_TYPE_KEY: Record<string, string> = {
  thesis: "claims.type.thesis",
  antithesis: "claims.type.antithesis",
  synthesis: "claims.type.synthesis",
  user_contributed: "claims.type.user_contributed",
  merged: "claims.type.merged",
};

const CLAIM_TYPE_COLOR: Record<string, string> = {
  thesis: "text-blue-600",
  antithesis: "text-blue-500",
  synthesis: "text-blue-700",
  user_contributed: "text-blue-600",
  merged: "text-blue-600",
};

const CONFIDENCE_BADGE: Record<string, string> = {
  speculative: "bg-blue-50 text-blue-500 border border-blue-200",
  emerging: "bg-blue-50 text-blue-600 border border-blue-200",
  grounded: "bg-blue-50 text-blue-700 border border-blue-200",
};

const CONFIDENCE_KEY: Record<string, string> = {
  speculative: "claims.confidence.speculative",
  emerging: "claims.confidence.emerging",
  grounded: "claims.confidence.grounded",
};

const SCORE_COLORS: Record<string, string> = {
  novelty: "bg-violet-500",
  groundedness: "bg-amber-500",
  falsifiability: "bg-cyan-500",
  significance: "bg-rose-500",
};

const SCORE_KEY: Record<string, string> = {
  novelty: "score.novelty",
  groundedness: "score.groundedness",
  falsifiability: "score.falsifiability",
  significance: "score.significance",
};

export default function ClaimCard({ claim, index, compact = false }: ClaimCardProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(!compact);

  const borderColor = claim.claim_type
    ? CLAIM_TYPE_BORDER[claim.claim_type] || "border-l-gray-300"
    : "border-l-gray-300";

  const typeKey = claim.claim_type ? CLAIM_TYPE_KEY[claim.claim_type] : null;
  const typeColor = claim.claim_type ? CLAIM_TYPE_COLOR[claim.claim_type] : null;

  const badgeClasses = claim.confidence
    ? CONFIDENCE_BADGE[claim.confidence] || "bg-gray-50 text-gray-600 border border-gray-200"
    : null;

  const hasDetails = claim.reasoning || claim.falsifiability_condition ||
    (claim.evidence && claim.evidence.length > 0) || claim.score_reasoning;

  return (
    <div className={`bg-white border border-gray-200/80 rounded-xl shadow-md shadow-gray-200/40 border-l-4 ${borderColor}`}>
      <div className={compact ? "p-4" : "p-5"}>
        {/* Header */}
        <div className="flex items-center gap-3 mb-3">
          {typeKey && typeColor && (
            <span className={`text-xs font-semibold uppercase tracking-wide ${typeColor}`}>
              {t(typeKey)}
            </span>
          )}
          {!typeKey && (
            <span className="text-xs text-gray-400 font-mono">#{index + 1}</span>
          )}
          {claim.confidence && badgeClasses && (
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${badgeClasses}`}>
              {t(CONFIDENCE_KEY[claim.confidence] || claim.confidence)}
            </span>
          )}
        </div>

        {/* Claim text — always visible */}
        <p className={`text-gray-900 font-medium leading-relaxed ${compact ? "text-sm" : "text-base"}`}>
          {claim.claim_text}
        </p>

        {/* Scores — always visible */}
        {claim.scores && (
          <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3">
            {Object.entries(claim.scores).map(([key, value]) =>
              value !== null ? (
                <div key={key}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-500 capitalize">{t(SCORE_KEY[key] || key)}</span>
                    <span className="text-xs text-gray-700 font-semibold tabular-nums">
                      {Math.round(value * 100)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-1.5">
                    <div
                      className={`${SCORE_COLORS[key] || "bg-blue-500"} h-1.5 rounded-full transition-all duration-300`}
                      style={{ width: `${value * 100}%` }}
                    />
                  </div>
                </div>
              ) : null
            )}
          </div>
        )}

        {/* Collapsible details in compact mode */}
        {compact && hasDetails && (
          <button
            onClick={() => setDetailsOpen(!detailsOpen)}
            className="mt-3 text-xs text-blue-600 hover:text-blue-500 font-medium"
          >
            {detailsOpen ? t("common.hide") : t("common.show")} {t("common.details")}
          </button>
        )}

        {detailsOpen && (
          <>
            {/* Reasoning */}
            {claim.reasoning && (
              <div className="mt-3 p-3 bg-gray-50 rounded-md border border-gray-100">
                <p className="text-xs text-gray-500 font-semibold mb-1 uppercase tracking-wide">{t("common.reasoning")}</p>
                <p className="text-gray-600 text-sm leading-relaxed">{claim.reasoning}</p>
              </div>
            )}

            {/* Falsifiability */}
            {claim.falsifiability_condition && (
              <div className="mt-3 p-3 bg-gray-50 rounded-md border border-gray-100">
                <p className="text-xs text-gray-500 font-semibold mb-1 uppercase tracking-wide">{t("common.falsifiability")}</p>
                <p className="text-gray-600 text-sm leading-relaxed">{claim.falsifiability_condition}</p>
              </div>
            )}

            {/* Evidence toggle */}
            {claim.evidence && claim.evidence.length > 0 && (
              <div className="mt-4">
                <button
                  onClick={() => setExpanded(!expanded)}
                  className="text-sm text-blue-600 hover:text-blue-500 font-medium"
                >
                  {expanded ? t("common.hide") : t("common.show")} {t("evidence.title")} ({claim.evidence.length})
                </button>
                {expanded && (
                  <div className="mt-2 space-y-2">
                    {claim.evidence.map((ev, i) => (
                      <div key={i} className="p-3 bg-gray-50 rounded-md border border-gray-100">
                        <a
                          href={ev.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-500 text-sm font-medium"
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
                <p className="text-xs text-gray-500 font-semibold mb-1 uppercase tracking-wide">{t("common.scoreReasoning")}</p>
                <p className="text-gray-600 text-sm leading-relaxed">{claim.score_reasoning}</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
