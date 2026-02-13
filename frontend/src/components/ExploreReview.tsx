import React, { useState } from "react";
import type { ExploreReviewData, UserInput } from "../types";

interface ExploreReviewProps {
  data: ExploreReviewData;
  onSubmit: (input: UserInput) => void;
}

export const ExploreReview: React.FC<ExploreReviewProps> = ({ data, onSubmit }) => {
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
    <div className="space-y-5 p-6 bg-white border border-gray-200 rounded-lg shadow-sm">
      {data.morphological_box && (
        <div>
          <h3 className="text-sm font-semibold text-blue-600 uppercase tracking-wide mb-3">Morphological Box</h3>
          <div className="overflow-x-auto">
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
        </div>
      )}

      <div>
        <h3 className="text-sm font-semibold text-blue-600 uppercase tracking-wide mb-3">Analogies</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {data.analogies.map((analogy, i) => (
            <div
              key={i}
              className={`p-4 rounded-lg border transition-all ${
                starredAnalogies.has(i)
                  ? "bg-blue-50 border-blue-300"
                  : "bg-gray-50 border-gray-200 hover:border-gray-300"
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                <h4 className="font-semibold text-gray-900 text-sm">{analogy.domain}</h4>
                <button
                  onClick={() => toggleStar(i)}
                  className={`text-sm font-medium px-2 py-0.5 rounded transition-colors ${
                    starredAnalogies.has(i)
                      ? "text-blue-600 bg-blue-100"
                      : "text-gray-400 hover:text-gray-600"
                  }`}
                >
                  {starredAnalogies.has(i) ? "Starred" : "Star"}
                </button>
              </div>
              <p className="text-gray-600 text-sm mb-2">{analogy.description}</p>
              {analogy.semantic_distance && (
                <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded border border-gray-200">
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
          placeholder="Suggest a new domain for analogy..."
          className="mt-3 w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-gray-700 text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      <div>
        <h3 className="text-sm font-semibold text-blue-600 uppercase tracking-wide mb-3">Contradictions</h3>
        <div className="space-y-2">
          {data.contradictions.map((contradiction, i) => (
            <div key={i} className="p-3 bg-gray-50 rounded-md border border-gray-100">
              <div className="flex items-center gap-2 mb-2">
                <span className="px-2 py-0.5 bg-rose-50 text-rose-700 border border-rose-200 rounded text-xs font-medium">
                  {contradiction.property_a}
                </span>
                <span className="text-gray-400 text-xs">vs</span>
                <span className="px-2 py-0.5 bg-rose-50 text-rose-700 border border-rose-200 rounded text-xs font-medium">
                  {contradiction.property_b}
                </span>
              </div>
              <p className="text-gray-600 text-sm">{contradiction.description}</p>
            </div>
          ))}
        </div>
      </div>

      <button
        onClick={handleSubmit}
        disabled={starredAnalogies.size === 0}
        className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed text-white font-medium text-sm rounded-md transition-colors"
      >
        Submit Review {starredAnalogies.size > 0 && `(${starredAnalogies.size} starred)`}
      </button>
    </div>
  );
};
