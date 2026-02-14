/**WebSearchCard — display-only web search result card.
 *
 * Invariants:
 *   - Shows query + result links in a compact collapsible card
 *   - No interactive buttons — purely informational
 *
 * Design Decisions:
 *   - Read-only display of links being researched (ADR: user requested removal of explore/skip buttons)
 *   - Collapsible to reduce visual noise when many searches occur
 */

import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import type { WebSearchResult } from "../types";

interface WebSearchCardProps {
  query: string;
  results: WebSearchResult[];
}

export const WebSearchCard: React.FC<WebSearchCardProps> = ({
  query,
  results,
}) => {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="bg-indigo-50/60 border border-indigo-200 rounded-lg p-3 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-2 h-2 rounded-full bg-indigo-400 flex-shrink-0" />
          <span className="text-xs font-semibold text-indigo-700 truncate">
            {query}
          </span>
        </div>
        {results.length > 0 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-indigo-400 hover:text-indigo-600 flex-shrink-0 ml-2"
          >
            {expanded ? t("research.collapse") : t("research.expand")}
          </button>
        )}
      </div>

      {/* Results */}
      {expanded && results.length > 0 && (
        <ul className="space-y-1 mt-2">
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
    </div>
  );
};
