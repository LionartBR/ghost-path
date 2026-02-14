/* DecomposeReview — Phase 1 review UI with 3 distinct section containers.

Invariants:
    - All assumptions start pending (user must select a dynamic option)
    - At least 1 reframing must be selected before submit
    - Carousel allows free navigation (prev/next) through assumptions
    - Option selection auto-advances to next card after brief visual feedback

Design Decisions:
    - 3 independent containers: Fundamentals, Assumptions, Reframings (ADR: clear visual hierarchy)
    - Each container has a Bootstrap Icon + colored left accent border for identity
    - Carousel over list: reduces cognitive load when 3+ assumptions (ADR: hackathon UX polish)
    - slideDirection state + key remount triggers CSS animation per direction
    - Auto-advance delay (300ms) lets user see the color feedback before slide
    - Dynamic options from model replace hardcoded Confirm/Reject (ADR: richer downstream context)
    - Fallback to Confirm/Reject if options array is empty (backward compat)
*/

import React, { useState, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import type { DecomposeReviewData, UserInput } from "../types";

interface DecomposeReviewProps {
  data: DecomposeReviewData;
  onSubmit: (input: UserInput) => void;
}

export const DecomposeReview: React.FC<DecomposeReviewProps> = ({ data, onSubmit }) => {
  const { t } = useTranslation();
  const [fundamentalsOpen, setFundamentalsOpen] = useState(false);
  const [assumptionResponses, setAssumptionResponses] = useState<Map<number, number>>(new Map());
  const [selectedReframings, setSelectedReframings] = useState<Set<number>>(new Set());
  const [newAssumption, setNewAssumption] = useState("");
  const [newReframing, setNewReframing] = useState("");

  const [currentCard, setCurrentCard] = useState(0);
  const [slideDirection, setSlideDirection] = useState<"left" | "right">("right");
  const autoAdvanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const totalAssumptions = data.assumptions.length;
  const isLastCard = currentCard >= totalAssumptions - 1;
  const isFirstCard = currentCard <= 0;

  const goToCard = useCallback((index: number, direction: "left" | "right") => {
    if (index < 0 || index >= totalAssumptions) return;
    setSlideDirection(direction);
    setCurrentCard(index);
  }, [totalAssumptions]);

  const goNext = useCallback(() => {
    if (!isLastCard) goToCard(currentCard + 1, "right");
  }, [currentCard, isLastCard, goToCard]);

  const goPrev = useCallback(() => {
    if (!isFirstCard) goToCard(currentCard - 1, "left");
  }, [currentCard, isFirstCard, goToCard]);

  const selectOption = useCallback((assumptionIndex: number, optionIndex: number) => {
    if (autoAdvanceTimer.current) clearTimeout(autoAdvanceTimer.current);

    setAssumptionResponses((prev) => {
      const next = new Map(prev);
      if (next.get(assumptionIndex) === optionIndex) {
        next.delete(assumptionIndex);
      } else {
        next.set(assumptionIndex, optionIndex);
      }
      return next;
    });

    if (assumptionIndex < totalAssumptions - 1) {
      autoAdvanceTimer.current = setTimeout(() => goNext(), 300);
    }
  }, [totalAssumptions, goNext]);

  const toggleReframing = (index: number) => {
    setSelectedReframings((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index); else next.add(index);
      return next;
    });
  };

  const handleSubmit = () => {
    const input: UserInput = {
      type: "decompose_review",
      assumption_responses: Array.from(assumptionResponses.entries()).map(
        ([idx, opt]) => ({ assumption_index: idx, selected_option: opt }),
      ),
      selected_reframings: Array.from(selectedReframings),
      added_assumptions: newAssumption.trim() ? [newAssumption.trim()] : undefined,
      added_reframings: newReframing.trim() ? [newReframing.trim()] : undefined,
    };
    onSubmit(input);
  };

  const isReviewed = (index: number): boolean => assumptionResponses.has(index);

  const assumption = data.assumptions[currentCard];

  const animationClass =
    slideDirection === "right" ? "animate-slide-in-right" : "animate-slide-in-left";

  return (
    <div className="space-y-4">
      {/* -- Fundamentals -- */}
      <div className="bg-white border border-gray-200/80 border-l-4 border-l-blue-400 rounded-xl shadow-sm p-5">
        <button
          onClick={() => setFundamentalsOpen(!fundamentalsOpen)}
          className="w-full flex items-center gap-2.5 text-sm font-semibold text-blue-600 uppercase tracking-wide hover:text-blue-500 transition-colors"
        >
          <i className="bi bi-diagram-3 text-base" />
          <span className="flex-1 text-left">
            {t("decompose.fundamentals")} ({data.fundamentals.length})
          </span>
          <span className={`transition-transform text-xs ${fundamentalsOpen ? "rotate-90" : ""}`}>
            &#9654;
          </span>
        </button>
        {fundamentalsOpen && (
          <ul className="mt-4 space-y-2">
            {data.fundamentals.map((fundamental, i) => (
              <li key={i} className="text-gray-700 text-sm flex items-start">
                <span className="text-blue-400 mr-2 mt-0.5">&bull;</span>
                {fundamental}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* -- Assumptions -- */}
      <div className="bg-white border border-gray-200/80 border-l-4 border-l-blue-400 rounded-xl shadow-sm p-5">
        <h3 className="flex items-center gap-2.5 text-sm font-semibold text-blue-600 uppercase tracking-wide mb-4">
          <i className="bi bi-patch-question text-base" />
          {t("decompose.assumptions")}
        </h3>

        {totalAssumptions > 0 && assumption && (
          <div className="flex flex-col items-center">
            {/* Progress dots */}
            <div className="flex items-center gap-1.5 mb-4">
              {data.assumptions.map((_, i) => {
                const reviewed = isReviewed(i);
                const dotColor = reviewed ? "bg-green-500" : "bg-gray-300";
                const ring = i === currentCard ? "ring-2 ring-blue-400 ring-offset-1" : "";
                return (
                  <button
                    key={i}
                    onClick={() => goToCard(i, i > currentCard ? "right" : "left")}
                    className={`w-2.5 h-2.5 rounded-full transition-all ${dotColor} ${ring}`}
                    aria-label={`Assumption ${i + 1}`}
                  />
                );
              })}
            </div>

            {/* Card + navigation */}
            <div className="flex items-center gap-3 w-full max-w-lg">
              {/* Prev arrow */}
              <button
                onClick={goPrev}
                disabled={isFirstCard}
                className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
                  isFirstCard
                    ? "text-gray-300 cursor-not-allowed"
                    : "text-gray-500 hover:bg-blue-50 hover:text-blue-600"
                }`}
                aria-label="Previous assumption"
              >
                <i className="bi bi-chevron-left text-lg" />
              </button>

              {/* Card */}
              <div
                key={currentCard}
                className={`flex-1 p-5 rounded-lg text-center ${animationClass}`}
              >
                <p className="text-xs text-gray-400 font-medium mb-2">
                  {currentCard + 1} / {totalAssumptions}
                </p>
                <p className="text-gray-700 text-sm leading-relaxed mb-4">
                  {assumption.text}
                </p>
                {/* Dynamic option buttons */}
                {assumption.options && assumption.options.length > 0 ? (
                  <div className="flex flex-col gap-2">
                    {assumption.options.map((option, optIdx) => {
                      const selected = assumptionResponses.get(currentCard) === optIdx;
                      return (
                        <button
                          key={optIdx}
                          onClick={() => selectOption(currentCard, optIdx)}
                          className={`w-full px-4 py-2 rounded-md text-xs font-medium transition-all text-left ${
                            selected
                              ? "bg-blue-500 text-white shadow-sm shadow-blue-200"
                              : "bg-white border border-gray-200 text-gray-600 hover:border-blue-300 hover:text-blue-600"
                          }`}
                        >
                          {option}
                        </button>
                      );
                    })}
                  </div>
                ) : (
                  /* Fallback: Confirm/Reject when no options provided */
                  <div className="flex justify-center gap-3">
                    <button
                      onClick={() => selectOption(currentCard, 0)}
                      className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-all inline-flex items-center gap-1.5 ${
                        assumptionResponses.get(currentCard) === 0
                          ? "bg-blue-500 text-white shadow-sm shadow-blue-200"
                          : "bg-white border border-gray-200 text-gray-600 hover:border-blue-300 hover:text-blue-600"
                      }`}
                    >
                      <i className="bi bi-check-lg" />
                      {t("decompose.confirm")}
                    </button>
                    <button
                      onClick={() => selectOption(currentCard, 1)}
                      className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-all inline-flex items-center gap-1.5 ${
                        assumptionResponses.get(currentCard) === 1
                          ? "bg-blue-400 text-white shadow-sm shadow-blue-200"
                          : "bg-white border border-gray-200 text-gray-600 hover:border-blue-300 hover:text-blue-600"
                      }`}
                    >
                      <i className="bi bi-x-lg" />
                      {t("decompose.reject")}
                    </button>
                  </div>
                )}
              </div>

              {/* Next arrow */}
              <button
                onClick={goNext}
                disabled={isLastCard}
                className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
                  isLastCard
                    ? "text-gray-300 cursor-not-allowed"
                    : "text-gray-500 hover:bg-blue-50 hover:text-blue-600"
                }`}
                aria-label="Next assumption"
              >
                <i className="bi bi-chevron-right text-lg" />
              </button>
            </div>
          </div>
        )}

        <input
          type="text"
          value={newAssumption}
          onChange={(e) => setNewAssumption(e.target.value)}
          placeholder={t("decompose.addAssumption")}
          className="mt-4 w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-gray-700 text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent"
        />
      </div>

      {/* -- Reframings -- */}
      <div className="bg-white border border-gray-200/80 border-l-4 border-l-blue-400 rounded-xl shadow-sm p-5">
        <h3 className="flex items-center gap-2.5 text-sm font-semibold text-blue-600 uppercase tracking-wide mb-4">
          <i className="bi bi-shuffle text-base" />
          {t("decompose.reframings")}
        </h3>
        <div className="space-y-2">
          {data.reframings.map((reframing, i) => (
            <label
              key={i}
              className={`flex items-start p-3 rounded-md border cursor-pointer transition-all ${
                selectedReframings.has(i)
                  ? "bg-blue-50 border-blue-200"
                  : "bg-gray-50 border-gray-100 hover:bg-gray-100"
              }`}
            >
              <input
                type="checkbox"
                checked={selectedReframings.has(i)}
                onChange={() => toggleReframing(i)}
                className="mt-0.5 mr-3 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <div>
                <p className="text-gray-700 text-sm">{reframing.text}</p>
                <p className="text-xs text-gray-400 mt-1 inline-flex items-center gap-1">
                  <i className="bi bi-tag text-[10px]" />
                  {reframing.type}
                </p>
              </div>
            </label>
          ))}
        </div>
        <input
          type="text"
          value={newReframing}
          onChange={(e) => setNewReframing(e.target.value)}
          placeholder={t("decompose.addReframing")}
          className="mt-3 w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-gray-700 text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent"
        />
      </div>

      {/* -- Submit -- */}
      <button
        onClick={handleSubmit}
        disabled={selectedReframings.size === 0}
        className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-200 disabled:text-gray-400 disabled:shadow-none disabled:cursor-not-allowed text-white font-semibold text-sm rounded-lg shadow-md shadow-blue-200/50 hover:shadow-lg hover:shadow-blue-300/50 transition-all inline-flex items-center justify-center gap-2"
      >
        {t("decompose.submitReview")}
      </button>
    </div>
  );
};
