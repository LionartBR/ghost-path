import React, { useState } from "react";
import type { DecomposeReviewData, UserInput } from "../types";

interface DecomposeReviewProps {
  data: DecomposeReviewData;
  onSubmit: (input: UserInput) => void;
}

export const DecomposeReview: React.FC<DecomposeReviewProps> = ({ data, onSubmit }) => {
  const [confirmedAssumptions, setConfirmedAssumptions] = useState<Set<number>>(new Set());
  const [rejectedAssumptions, setRejectedAssumptions] = useState<Set<number>>(new Set());
  const [selectedReframings, setSelectedReframings] = useState<Set<number>>(new Set());
  const [newAssumption, setNewAssumption] = useState("");
  const [newReframing, setNewReframing] = useState("");

  const toggleAssumption = (index: number, type: "confirm" | "reject") => {
    if (type === "confirm") {
      setConfirmedAssumptions((prev) => {
        const next = new Set(prev);
        next.has(index) ? next.delete(index) : next.add(index);
        return next;
      });
      setRejectedAssumptions((prev) => {
        const next = new Set(prev);
        next.delete(index);
        return next;
      });
    } else {
      setRejectedAssumptions((prev) => {
        const next = new Set(prev);
        next.has(index) ? next.delete(index) : next.add(index);
        return next;
      });
      setConfirmedAssumptions((prev) => {
        const next = new Set(prev);
        next.delete(index);
        return next;
      });
    }
  };

  const toggleReframing = (index: number) => {
    setSelectedReframings((prev) => {
      const next = new Set(prev);
      next.has(index) ? next.delete(index) : next.add(index);
      return next;
    });
  };

  const handleSubmit = () => {
    const input: UserInput = {
      type: "decompose_review",
      confirmed_assumptions: Array.from(confirmedAssumptions),
      rejected_assumptions: Array.from(rejectedAssumptions),
      selected_reframings: Array.from(selectedReframings),
      added_assumptions: newAssumption.trim() ? [newAssumption.trim()] : undefined,
      added_reframings: newReframing.trim() ? [newReframing.trim()] : undefined,
    };
    onSubmit(input);
  };

  return (
    <div className="space-y-6 p-6 bg-gray-800 rounded-lg">
      <div>
        <h3 className="text-xl font-bold text-purple-400 mb-3">Fundamentals</h3>
        <ul className="space-y-2">
          {data.fundamentals.map((fundamental, i) => (
            <li key={i} className="text-gray-300 flex items-start">
              <span className="text-purple-500 mr-2">•</span>
              {fundamental}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="text-xl font-bold text-purple-400 mb-3">Assumptions</h3>
        <div className="space-y-3">
          {data.assumptions.map((assumption, i) => (
            <div key={i} className="p-3 bg-gray-900 rounded border border-gray-700">
              <p className="text-gray-300 mb-2">{assumption.text}</p>
              <div className="flex gap-3">
                <button
                  onClick={() => toggleAssumption(i, "confirm")}
                  className={`px-3 py-1 rounded text-sm ${
                    confirmedAssumptions.has(i)
                      ? "bg-green-600 text-white"
                      : "bg-gray-700 text-gray-400 hover:bg-gray-600"
                  }`}
                >
                  Confirm
                </button>
                <button
                  onClick={() => toggleAssumption(i, "reject")}
                  className={`px-3 py-1 rounded text-sm ${
                    rejectedAssumptions.has(i)
                      ? "bg-red-600 text-white"
                      : "bg-gray-700 text-gray-400 hover:bg-gray-600"
                  }`}
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
        <input
          type="text"
          value={newAssumption}
          onChange={(e) => setNewAssumption(e.target.value)}
          placeholder="Add new assumption..."
          className="mt-3 w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-gray-300 placeholder-gray-500"
        />
      </div>

      <div>
        <h3 className="text-xl font-bold text-purple-400 mb-3">Reframings</h3>
        <div className="space-y-2">
          {data.reframings.map((reframing, i) => (
            <label key={i} className="flex items-start p-3 bg-gray-900 rounded border border-gray-700 cursor-pointer hover:bg-gray-850">
              <input
                type="checkbox"
                checked={selectedReframings.has(i)}
                onChange={() => toggleReframing(i)}
                className="mt-1 mr-3"
              />
              <div>
                <p className="text-gray-300">{reframing.text}</p>
                <p className="text-xs text-gray-500 mt-1">Type: {reframing.type}</p>
              </div>
            </label>
          ))}
        </div>
        <input
          type="text"
          value={newReframing}
          onChange={(e) => setNewReframing(e.target.value)}
          placeholder="Add new reframing..."
          className="mt-3 w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-gray-300 placeholder-gray-500"
        />
      </div>

      <button
        onClick={handleSubmit}
        className="w-full py-3 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded transition-colors"
      >
        Submit Review
      </button>
    </div>
  );
};
