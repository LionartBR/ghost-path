/* ExploreReview — Phase 2 review UI with 3 distinct section containers.

Invariants:
    - At least 1 analogy must be starred before submit
    - Morphological box and contradictions are collapsible (read-only context)
    - User can suggest additional domains for analogy search

Design Decisions:
    - 3 independent containers: Morphological Box, Analogies, Contradictions (ADR: clear visual hierarchy)
    - Each container has a Bootstrap Icon + colored left accent border for identity
    - Star toggle uses bi-star / bi-star-fill for immediate visual feedback
    - Semantic distance badge stays inline with analogy card
*/

import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import type { ExploreReviewData, UserInput } from "../types";

interface ExploreReviewProps {
  data: ExploreReviewData;
  onSubmit: (input: UserInput) => void;
}

export const ExploreReview: React.FC<ExploreReviewProps> = ({ data, onSubmit }) => {
  const { t } = useTranslation();
  const [morphBoxOpen, setMorphBoxOpen] = useState(false);
  const [contradictionsOpen, setContradictionsOpen] = useState(false);
  const [starredAnalogies, setStarredAnalogies] = useState<Set<number>>(new Set());
  const [newDomain, setNewDomain] = useState("");

  const toggleStar = (index: number) => {
    setStarredAnalogies((prev) => {
      const next = new Set(prev);
      next.has(index) ? next.delete(index) : next.add(index);
      return next;
    });
  };

  const handleSubmit = () => {
    const input: UserInput = {
      type: "explore_review",
      starred_analogies: Array.from(starredAnalogies),
      suggested_domains: newDomain.trim() ? [newDomain.trim()] : undefined,
    };
    onSubmit(input);
  };

  return (
    <div className="space-y-4">
      {/* ── Morphological Box ── */}
      {data.morphological_box && (
        <div className="bg-white border border-gray-200/80 border-l-4 border-l-blue-400 rounded-xl shadow-sm p-5">
          <button
            onClick={() => setMorphBoxOpen(!morphBoxOpen)}
            className="w-full flex items-center gap-2.5 text-sm font-semibold text-blue-600 uppercase tracking-wide hover:text-blue-500 transition-colors"
          >
            <i className="bi bi-grid-3x3-gap text-base" />
            <span className="flex-1 text-left">
              {t("explore.morphBox")} ({data.morphological_box.parameters.length})
            </span>
            <span className={`transition-transform text-xs ${morphBoxOpen ? "rotate-90" : ""}`}>
              &#9654;
            </span>
          </button>
          {morphBoxOpen && (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    {data.morphological_box.parameters.map((param, i) => (
                      <th
                        key={i}
                        className="px-3 py-2 bg-blue-50 text-blue-700 text-left text-xs font-semibold uppercase tracking-wide border border-gray-200"
                      >
                        {param.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Array.from({
                    length: Math.max(
                      ...data.morphological_box.parameters.map((p) => p.values.length)
                    ),
                  }).map((_, rowIndex) => (
                    <tr key={rowIndex}>
                      {data.morphological_box!.parameters.map((param, colIndex) => (
                        <td
                          key={colIndex}
                          className="px-3 py-2 text-gray-700 text-sm border border-gray-200"
                        >
                          {param.values[rowIndex] || ""}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── Analogies ── */}
      <div className="bg-white border border-gray-200/80 border-l-4 border-l-teal-400 rounded-xl shadow-sm p-5">
        <h3 className="flex items-center gap-2.5 text-sm font-semibold text-teal-600 uppercase tracking-wide mb-4">
          <i className="bi bi-globe2 text-base" />
          {t("explore.analogies")}
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {data.analogies.map((analogy, i) => (
            <div
              key={i}
              className={`p-4 rounded-lg border transition-all ${
                starredAnalogies.has(i)
                  ? "bg-teal-50 border-teal-300"
                  : "bg-gray-50 border-gray-200 hover:border-gray-300"
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                <h4 className="font-semibold text-gray-900 text-sm">{analogy.domain}</h4>
                <button
                  onClick={() => toggleStar(i)}
                  className={`text-sm font-medium px-2 py-0.5 rounded transition-colors inline-flex items-center gap-1 ${
                    starredAnalogies.has(i)
                      ? "text-teal-600 bg-teal-100"
                      : "text-gray-400 hover:text-gray-600"
                  }`}
                >
                  <i className={`bi ${starredAnalogies.has(i) ? "bi-star-fill" : "bi-star"}`} />
                  {starredAnalogies.has(i) ? t("explore.starred") : t("explore.star")}
                </button>
              </div>
              <p className="text-gray-600 text-sm mb-2">{analogy.description}</p>
              {analogy.semantic_distance && (
                <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded border border-gray-200 inline-flex items-center gap-1">
                  <i className="bi bi-rulers text-[10px]" />
                  {analogy.semantic_distance}
                </span>
              )}
            </div>
          ))}
        </div>
        <input
          type="text"
          value={newDomain}
          onChange={(e) => setNewDomain(e.target.value)}
          placeholder={t("explore.suggestDomain")}
          className="mt-3 w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-gray-700 text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-transparent"
        />
      </div>

      {/* ── Contradictions ── */}
      <div className="bg-white border border-gray-200/80 border-l-4 border-l-rose-400 rounded-xl shadow-sm p-5">
        <button
          onClick={() => setContradictionsOpen(!contradictionsOpen)}
          className="w-full flex items-center gap-2.5 text-sm font-semibold text-rose-600 uppercase tracking-wide hover:text-rose-500 transition-colors"
        >
          <i className="bi bi-arrow-left-right text-base" />
          <span className="flex-1 text-left">
            {t("explore.contradictions")} ({data.contradictions.length})
          </span>
          <span className={`transition-transform text-xs ${contradictionsOpen ? "rotate-90" : ""}`}>
            &#9654;
          </span>
        </button>
        {contradictionsOpen && (
          <div className="mt-4 space-y-2">
            {data.contradictions.map((contradiction, i) => (
              <div key={i} className="p-3 bg-gray-50 rounded-md border border-gray-100">
                <div className="flex items-center gap-2 mb-2">
                  <span className="px-2 py-0.5 bg-rose-50 text-rose-700 border border-rose-200 rounded text-xs font-medium">
                    {contradiction.property_a}
                  </span>
                  <i className="bi bi-arrow-left-right text-gray-400 text-xs" />
                  <span className="px-2 py-0.5 bg-rose-50 text-rose-700 border border-rose-200 rounded text-xs font-medium">
                    {contradiction.property_b}
                  </span>
                </div>
                <p className="text-gray-600 text-sm">{contradiction.description}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Submit ── */}
      <button
        onClick={handleSubmit}
        disabled={starredAnalogies.size === 0}
        className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-200 disabled:text-gray-400 disabled:shadow-none disabled:cursor-not-allowed text-white font-semibold text-sm rounded-lg shadow-md shadow-blue-200/50 hover:shadow-lg hover:shadow-blue-300/50 transition-all inline-flex items-center justify-center gap-2"
      >
        <i className="bi bi-send" />
        {starredAnalogies.size > 0
          ? t("explore.submitReview", { count: starredAnalogies.size })
          : t("explore.submitReviewNone")}
      </button>
    </div>
  );
};
