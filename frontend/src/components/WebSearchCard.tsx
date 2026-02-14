/**WebSearchCard — interactive web search result card with research directives.
 *
 * Invariants:
 *   - Upgrades from purple pill in-place (same activity item slot)
 *   - Buttons disabled when stream ends or directive already sent
 *   - Domain extracted heuristically from query for directive payload
 *
 * Design Decisions:
 *   - "Explore More" / "Skip" pattern mirrors user agency during passive streaming
 *   - Sent state locks buttons to prevent duplicate directives (ADR: idempotency)
 */

import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import type { WebSearchResult } from "../types";

interface WebSearchCardProps {
  query: string;
  results: WebSearchResult[];
  directiveSent: boolean;
  isStreaming: boolean;
  onDirective: (type: "explore_more" | "skip_domain", query: string, domain: string) => void;
}

function extractDomain(query: string): string {
  const words = query.split(/\s+/).filter((w) => w.length > 3);
  return words[words.length - 1] || query;
}

export const WebSearchCard: React.FC<WebSearchCardProps> = ({
  query,
  results,
  directiveSent,
  isStreaming,
  onDirective,
}) => {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(true);
  const domain = extractDomain(query);
  const canAct = isStreaming && !directiveSent;

  return (
    <div className="bg-indigo-50/60 border border-indigo-200 rounded-lg p-3 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-indigo-400" />
          <span className="text-xs font-semibold text-indigo-700 truncate max-w-[260px]">
            {query}
          </span>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-indigo-400 hover:text-indigo-600"
        >
          {expanded ? t("research.collapse") : t("research.expand")}
        </button>
      </div>

      {/* Results */}
      {expanded && results.length > 0 && (
        <ul className="space-y-1 mb-2.5">
          {results.map((r, i) => (
            <li key={i} className="flex items-start gap-1.5">
              <span className="text-indigo-300 text-xs mt-0.5">-</span>
              <a
                href={r.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-indigo-600 hover:text-indigo-500 underline decoration-indigo-300 truncate"
                title={r.url}
              >
                {r.title || r.url}
              </a>
            </li>
          ))}
        </ul>
      )}

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          disabled={!canAct}
          onClick={() => onDirective("explore_more", query, domain)}
          className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
            directiveSent
              ? "bg-indigo-100 text-indigo-400 cursor-default"
              : canAct
                ? "bg-indigo-600 text-white hover:bg-indigo-700"
                : "bg-gray-100 text-gray-400 cursor-not-allowed"
          }`}
        >
          {directiveSent ? t("research.sent") : t("research.exploreMore")}
        </button>
        <button
          disabled={!canAct}
          onClick={() => onDirective("skip_domain", query, domain)}
          className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
            directiveSent
              ? "bg-gray-100 text-gray-400 cursor-default"
              : canAct
                ? "bg-gray-200 text-gray-600 hover:bg-gray-300"
                : "bg-gray-100 text-gray-400 cursor-not-allowed"
          }`}
        >
          {directiveSent ? t("research.sent") : t("research.skip")}
        </button>
      </div>
    </div>
  );
};
