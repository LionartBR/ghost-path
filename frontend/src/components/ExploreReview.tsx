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
    <div className="space-y-6 p-6 bg-gray-800 rounded-lg">
      {data.morphological_box && (
        <div>
          <h3 className="text-xl font-bold text-blue-400 mb-3">Morphological Box</h3>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  {data.morphological_box.parameters.map((param, i) => (
                    <th
                      key={i}
                      className="px-3 py-2 bg-gray-900 text-blue-300 text-left border border-gray-700"
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
                        className="px-3 py-2 text-gray-300 border border-gray-700"
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
        <h3 className="text-xl font-bold text-blue-400 mb-3">Analogies</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.analogies.map((analogy, i) => (
            <div
              key={i}
              className={`p-4 rounded border transition-all ${
                starredAnalogies.has(i)
                  ? "bg-blue-900 border-blue-500"
                  : "bg-gray-900 border-gray-700"
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                <h4 className="font-bold text-blue-300">{analogy.domain}</h4>
                <button
                  onClick={() => toggleStar(i)}
                  className="text-2xl transition-colors"
                >
                  {starredAnalogies.has(i) ? "⭐" : "☆"}
                </button>
              </div>
              <p className="text-gray-300 text-sm mb-2">{analogy.description}</p>
              {analogy.semantic_distance && (
                <p className="text-xs text-gray-500">
                  Distance: {analogy.semantic_distance}
                </p>
              )}
            </div>
          ))}
        </div>
        <input
          type="text"
          value={newDomain}
          onChange={(e) => setNewDomain(e.target.value)}
          placeholder="Suggest a new domain for analogy..."
          className="mt-4 w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-gray-300 placeholder-gray-500"
        />
      </div>

      <div>
        <h3 className="text-xl font-bold text-blue-400 mb-3">Contradictions</h3>
        <div className="space-y-3">
          {data.contradictions.map((contradiction, i) => (
            <div key={i} className="p-3 bg-gray-900 rounded border border-gray-700">
              <div className="flex items-center gap-3 mb-2">
                <span className="px-2 py-1 bg-red-900 text-red-300 rounded text-sm">
                  {contradiction.property_a}
                </span>
                <span className="text-gray-500">vs</span>
                <span className="px-2 py-1 bg-red-900 text-red-300 rounded text-sm">
                  {contradiction.property_b}
                </span>
              </div>
              <p className="text-gray-300 text-sm">{contradiction.description}</p>
            </div>
          ))}
        </div>
      </div>

      <button
        onClick={handleSubmit}
        disabled={starredAnalogies.size === 0}
        className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-bold rounded transition-colors"
      >
        Submit Review {starredAnalogies.size > 0 && `(${starredAnalogies.size} starred)`}
      </button>
    </div>
  );
};
