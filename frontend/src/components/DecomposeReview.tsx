import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import type { DecomposeReviewData, UserInput } from "../types";

interface DecomposeReviewProps {
  data: DecomposeReviewData;
  onSubmit: (input: UserInput) => void;
}

export const DecomposeReview: React.FC<DecomposeReviewProps> = ({ data, onSubmit }) => {
  const { t } = useTranslation();
  const [fundamentalsOpen, setFundamentalsOpen] = useState(false);
  const [confirmedAssumptions, setConfirmedAssumptions] = useState<Set<number>>(
    () => new Set(data.assumptions.map((_, i) => i))
  );
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
    <div className="space-y-5 p-6 bg-white border border-gray-200 rounded-lg shadow-sm">
      <div>
        <button
          onClick={() => setFundamentalsOpen(!fundamentalsOpen)}
          className="flex items-center gap-2 text-sm font-semibold text-indigo-600 uppercase tracking-wide mb-3 hover:text-indigo-500 transition-colors"
        >
          <span className={`transition-transform ${fundamentalsOpen ? "rotate-90" : ""}`}>&#9654;</span>
          {t("decompose.fundamentals")} ({data.fundamentals.length})
        </button>
        {fundamentalsOpen && (
          <ul className="space-y-2">
            {data.fundamentals.map((fundamental, i) => (
              <li key={i} className="text-gray-700 text-sm flex items-start">
                <span className="text-indigo-400 mr-2 mt-0.5">&bull;</span>
                {fundamental}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <h3 className="text-sm font-semibold text-indigo-600 uppercase tracking-wide mb-3">{t("decompose.assumptions")}</h3>
        <div className="space-y-2">
          {data.assumptions.map((assumption, i) => (
            <div key={i} className="p-3 bg-gray-50 rounded-md border border-gray-100">
              <p className="text-gray-700 text-sm mb-2">{assumption.text}</p>
              <div className="flex gap-2">
                <button
                  onClick={() => toggleAssumption(i, "confirm")}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                    confirmedAssumptions.has(i)
                      ? "bg-green-500 text-white"
                      : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  {t("decompose.confirm")}
                </button>
                <button
                  onClick={() => toggleAssumption(i, "reject")}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                    rejectedAssumptions.has(i)
                      ? "bg-red-500 text-white"
                      : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  {t("decompose.reject")}
                </button>
              </div>
            </div>
          ))}
        </div>
        <input
          type="text"
          value={newAssumption}
          onChange={(e) => setNewAssumption(e.target.value)}
          placeholder={t("decompose.addAssumption")}
          className="mt-3 w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-gray-700 text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        />
      </div>

      <div>
        <h3 className="text-sm font-semibold text-indigo-600 uppercase tracking-wide mb-3">{t("decompose.reframings")}</h3>
        <div className="space-y-2">
          {data.reframings.map((reframing, i) => (
            <label key={i} className="flex items-start p-3 bg-gray-50 rounded-md border border-gray-100 cursor-pointer hover:bg-gray-100 transition-colors">
              <input
                type="checkbox"
                checked={selectedReframings.has(i)}
                onChange={() => toggleReframing(i)}
                className="mt-0.5 mr-3 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <div>
                <p className="text-gray-700 text-sm">{reframing.text}</p>
                <p className="text-xs text-gray-400 mt-1">Type: {reframing.type}</p>
              </div>
            </label>
          ))}
        </div>
        <input
          type="text"
          value={newReframing}
          onChange={(e) => setNewReframing(e.target.value)}
          placeholder={t("decompose.addReframing")}
          className="mt-3 w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-gray-700 text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        />
      </div>

      <button
        onClick={handleSubmit}
        className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm rounded-md transition-colors"
      >
        {t("decompose.submitReview")}
      </button>
    </div>
  );
};
