/* DecomposeReview — Phase 1 review UI with 2 section containers (Assumptions + Reframings).

Invariants:
    - All assumptions start pending (user must select a dynamic option)
    - At least 1 reframing must be selected before submit
    - Carousel allows free navigation (prev/next) through assumptions
    - Option selection auto-advances to next card after brief visual feedback

Design Decisions:
    - Fundamentals hidden from UI but still sent as context to the model (ADR: reduce visual noise)
    - 2 containers: Assumptions, Reframings — gray left accent by default, green on completion
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
  const [assumptionResponses, setAssumptionResponses] = useState<Map<number, number>>(new Map());
  const [selectedReframings, setSelectedReframings] = useState<Set<number>>(new Set());
  const [newAssumption, setNewAssumption] = useState("");
  const [newReframing, setNewReframing] = useState("");

  const [currentCard, setCurrentCard] = useState(0);
  const [slideDirection, setSlideDirection] = useState<"left" | "right">("right");
  const autoAdvanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [assumptionsDone, setAssumptionsDone] = useState(false);
  const [assumptionsCollapsed, setAssumptionsCollapsed] = useState(false);

  const totalAssumptions = data.assumptions.length;
  const allAssumptionsReviewed = totalAssumptions > 0 && assumptionResponses.size >= totalAssumptions;
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

      // Check if all assumptions are now reviewed
      if (next.size >= totalAssumptions) {
        autoAdvanceTimer.current = setTimeout(() => {
          setAssumptionsDone(true);
          setAssumptionsCollapsed(true);
        }, 400);
      } else if (assumptionIndex < totalAssumptions - 1) {
        autoAdvanceTimer.current = setTimeout(() => goNext(), 300);
      }

      return next;
    });
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
      {/* -- Assumptions -- */}
      {assumptionsCollapsed ? (
        /* Collapsed summary — click to re-expand */
        <div
          onClick={() => { setAssumptionsCollapsed(false); setAssumptionsDone(false); }}
          className="bg-white border border-gray-200/80 border-l-4 border-l-green-500 rounded-xl shadow-sm p-4 cursor-pointer hover:bg-green-50/30 transition-colors animate-fade-in"
        >
          <div className="flex items-center gap-2.5">
            <i className="bi bi-patch-check-fill text-green-500 text-base" />
            <span className="text-sm font-semibold text-green-600 uppercase tracking-wide flex-1">
              {t("decompose.assumptions")} ({totalAssumptions}/{totalAssumptions})
            </span>
            <span className="text-xs text-gray-400 flex items-center gap-1">
              <i className="bi bi-pencil text-[10px]" />
              {t("decompose.edit")}
            </span>
          </div>
        </div>
      ) : (
        <div className={`bg-white border border-gray-200/80 border-l-4 rounded-xl shadow-sm p-5 transition-all ${
          allAssumptionsReviewed ? "border-l-green-500" : "border-l-gray-300"
        } ${assumptionsDone ? "animate-fade-in" : ""}`}>
          <h3 className={`flex items-center gap-2.5 text-sm font-semibold uppercase tracking-wide mb-4 ${
            allAssumptionsReviewed ? "text-green-600" : "text-gray-400"
          }`}>
            <i className="bi bi-patch-question text-base" />
            {t("decompose.assumptions")}
            {allAssumptionsReviewed && (
              <span className="ml-auto text-xs text-green-500 font-normal flex items-center gap-1">
                <i className="bi bi-check-circle-fill text-[11px]" />
              </span>
            )}
          </h3>

          {totalAssumptions > 0 && assumption && (
            <div className="flex flex-col items-center">
              {/* Progress dots */}
              <div className="flex items-center gap-1.5 mb-4">
                {data.assumptions.map((_, i) => {
                  const reviewed = isReviewed(i);
                  const dotColor = reviewed ? "bg-green-500" : "bg-gray-300";
                  const ring = i === currentCard ? "ring-2 ring-green-400 ring-offset-1" : "";
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
                      : "text-gray-500 hover:bg-green-50 hover:text-green-600"
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
                                ? "bg-green-500 text-white shadow-sm shadow-green-200"
                                : "bg-white border border-gray-200 text-gray-600 hover:border-green-300 hover:text-green-600"
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
                            ? "bg-green-500 text-white shadow-sm shadow-green-200"
                            : "bg-white border border-gray-200 text-gray-600 hover:border-green-300 hover:text-green-600"
                        }`}
                      >
                        <i className="bi bi-check-lg" />
                        {t("decompose.confirm")}
                      </button>
                      <button
                        onClick={() => selectOption(currentCard, 1)}
                        className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-all inline-flex items-center gap-1.5 ${
                          assumptionResponses.get(currentCard) === 1
                            ? "bg-green-400 text-white shadow-sm shadow-green-200"
                            : "bg-white border border-gray-200 text-gray-600 hover:border-green-300 hover:text-green-600"
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
                      : "text-gray-500 hover:bg-green-50 hover:text-green-600"
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
            className="mt-4 w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-gray-700 text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-400 focus:border-transparent"
          />
        </div>
      )}

      {/* -- Reframings (appears after all assumptions reviewed) -- */}
      {allAssumptionsReviewed && (
        <div className={`bg-white border border-gray-200/80 border-l-4 rounded-xl shadow-sm p-5 animate-fade-in ${
          selectedReframings.size > 0 ? "border-l-green-500" : "border-l-gray-300"
        }`}>
          <h3 className={`flex items-center gap-2.5 text-sm font-semibold uppercase tracking-wide mb-4 ${
            selectedReframings.size > 0 ? "text-green-600" : "text-gray-400"
          }`}>
            <i className="bi bi-shuffle text-base" />
            {t("decompose.reframings")}
            {selectedReframings.size > 0 && (
              <span className="ml-auto text-xs text-green-500 font-normal flex items-center gap-1">
                <i className="bi bi-check-circle-fill text-[11px]" />
              </span>
            )}
          </h3>
          <div className="space-y-2">
            {data.reframings.map((reframing, i) => (
              <label
                key={i}
                className={`flex items-start p-3 rounded-md border cursor-pointer transition-all ${
                  selectedReframings.has(i)
                    ? "bg-green-50 border-green-200"
                    : "bg-gray-50 border-gray-100 hover:bg-gray-100"
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedReframings.has(i)}
                  onChange={() => toggleReframing(i)}
                  className="mt-0.5 mr-3 rounded border-gray-300 text-green-600 focus:ring-green-500"
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
            className="mt-3 w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-gray-700 text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-400 focus:border-transparent"
          />
        </div>
      )}

      {/* -- Submit (only after assumptions reviewed) -- */}
      {allAssumptionsReviewed && (
        <button
          onClick={handleSubmit}
          disabled={selectedReframings.size === 0}
          className="w-full py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-200 disabled:text-gray-400 disabled:shadow-none disabled:cursor-not-allowed text-white font-semibold text-sm rounded-lg shadow-md shadow-green-200/50 hover:shadow-lg hover:shadow-green-300/50 transition-all inline-flex items-center justify-center gap-2 animate-fade-in"
        >
          {t("decompose.submitReview")}
        </button>
      )}
    </div>
  );
};
