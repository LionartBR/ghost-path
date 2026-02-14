/* DecomposeReview — Phase 1 review UI with 3 distinct section containers.

Invariants:
    - All assumptions start pending (user must explicitly confirm or reject)
    - At least 1 reframing must be selected before submit
    - Carousel allows free navigation (prev/next) through assumptions
    - Confirm/Reject auto-advances to next card after brief visual feedback

Design Decisions:
    - 3 independent containers: Fundamentals, Assumptions, Reframings (ADR: clear visual hierarchy)
    - Each container has a Bootstrap Icon + colored left accent border for identity
    - Carousel over list: reduces cognitive load when 3+ assumptions (ADR: hackathon UX polish)
    - slideDirection state + key remount triggers CSS animation per direction
    - Auto-advance delay (300ms) lets user see the color feedback before slide
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
  const [confirmedAssumptions, setConfirmedAssumptions] = useState<Set<number>>(new Set());
  const [rejectedAssumptions, setRejectedAssumptions] = useState<Set<number>>(new Set());
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

  const toggleAssumption = useCallback((index: number, type: "confirm" | "reject") => {
    if (autoAdvanceTimer.current) clearTimeout(autoAdvanceTimer.current);

    if (type === "confirm") {
      setConfirmedAssumptions((prev) => {
        const next = new Set(prev);
        if (next.has(index)) next.delete(index); else next.add(index);
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
        if (next.has(index)) next.delete(index); else next.add(index);
        return next;
      });
      setConfirmedAssumptions((prev) => {
        const next = new Set(prev);
        next.delete(index);
        return next;
      });
    }

    if (index < totalAssumptions - 1) {
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
      confirmed_assumptions: Array.from(confirmedAssumptions),
      rejected_assumptions: Array.from(rejectedAssumptions),
      selected_reframings: Array.from(selectedReframings),
      added_assumptions: newAssumption.trim() ? [newAssumption.trim()] : undefined,
      added_reframings: newReframing.trim() ? [newReframing.trim()] : undefined,
    };
    onSubmit(input);
  };

  const cardStatus = (index: number): "confirmed" | "rejected" | "pending" => {
    if (confirmedAssumptions.has(index)) return "confirmed";
    if (rejectedAssumptions.has(index)) return "rejected";
    return "pending";
  };

  const assumption = data.assumptions[currentCard];
  const status = assumption ? cardStatus(currentCard) : "pending";

  const animationClass =
    slideDirection === "right" ? "animate-slide-in-right" : "animate-slide-in-left";

  return (
    <div className="space-y-4">
      {/* ── Phase Header ── */}
      <div className="bg-white border border-gray-200/80 rounded-xl shadow-md shadow-gray-200/40 p-5">
        <h2 className="text-base font-semibold text-gray-900 mb-1">
          {t("decompose.title")}
        </h2>
        <p className="text-gray-500 text-sm">
          {t("decompose.description")}
        </p>
      </div>

      {/* ── Fundamentals ── */}
      <div className="bg-white border border-gray-200/80 border-l-4 border-l-indigo-400 rounded-xl shadow-sm p-5">
        <button
          onClick={() => setFundamentalsOpen(!fundamentalsOpen)}
          className="w-full flex items-center gap-2.5 text-sm font-semibold text-indigo-600 uppercase tracking-wide hover:text-indigo-500 transition-colors"
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
                <span className="text-indigo-400 mr-2 mt-0.5">&bull;</span>
                {fundamental}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* ── Assumptions ── */}
      <div className="bg-white border border-gray-200/80 border-l-4 border-l-amber-400 rounded-xl shadow-sm p-5">
        <h3 className="flex items-center gap-2.5 text-sm font-semibold text-amber-600 uppercase tracking-wide mb-4">
          <i className="bi bi-patch-question text-base" />
          {t("decompose.assumptions")}
        </h3>

        {totalAssumptions > 0 && assumption && (
          <div className="flex flex-col items-center">
            {/* Progress dots */}
            <div className="flex items-center gap-1.5 mb-4">
              {data.assumptions.map((_, i) => {
                const s = cardStatus(i);
                const dotColor =
                  s === "confirmed"
                    ? "bg-green-500"
                    : s === "rejected"
                      ? "bg-red-500"
                      : "bg-gray-300";
                const ring = i === currentCard ? "ring-2 ring-amber-400 ring-offset-1" : "";
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
                    : "text-gray-500 hover:bg-amber-50 hover:text-amber-600"
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
                <div className="flex justify-center gap-3">
                  <button
                    onClick={() => toggleAssumption(currentCard, "confirm")}
                    className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-all inline-flex items-center gap-1.5 ${
                      confirmedAssumptions.has(currentCard)
                        ? "bg-green-500 text-white shadow-sm shadow-green-200"
                        : "bg-white border border-gray-200 text-gray-600 hover:border-green-300 hover:text-green-600"
                    }`}
                  >
                    <i className="bi bi-check-lg" />
                    {t("decompose.confirm")}
                  </button>
                  <button
                    onClick={() => toggleAssumption(currentCard, "reject")}
                    className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-all inline-flex items-center gap-1.5 ${
                      rejectedAssumptions.has(currentCard)
                        ? "bg-red-500 text-white shadow-sm shadow-red-200"
                        : "bg-white border border-gray-200 text-gray-600 hover:border-red-300 hover:text-red-600"
                    }`}
                  >
                    <i className="bi bi-x-lg" />
                    {t("decompose.reject")}
                  </button>
                </div>
              </div>

              {/* Next arrow */}
              <button
                onClick={goNext}
                disabled={isLastCard}
                className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
                  isLastCard
                    ? "text-gray-300 cursor-not-allowed"
                    : "text-gray-500 hover:bg-amber-50 hover:text-amber-600"
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
          className="mt-4 w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-gray-700 text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent"
        />
      </div>

      {/* ── Reframings ── */}
      <div className="bg-white border border-gray-200/80 border-l-4 border-l-violet-400 rounded-xl shadow-sm p-5">
        <h3 className="flex items-center gap-2.5 text-sm font-semibold text-violet-600 uppercase tracking-wide mb-4">
          <i className="bi bi-shuffle text-base" />
          {t("decompose.reframings")}
        </h3>
        <div className="space-y-2">
          {data.reframings.map((reframing, i) => (
            <label
              key={i}
              className={`flex items-start p-3 rounded-md border cursor-pointer transition-all ${
                selectedReframings.has(i)
                  ? "bg-violet-50 border-violet-200"
                  : "bg-gray-50 border-gray-100 hover:bg-gray-100"
              }`}
            >
              <input
                type="checkbox"
                checked={selectedReframings.has(i)}
                onChange={() => toggleReframing(i)}
                className="mt-0.5 mr-3 rounded border-gray-300 text-violet-600 focus:ring-violet-500"
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
          className="mt-3 w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-gray-700 text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent"
        />
      </div>

      {/* ── Submit ── */}
      <button
        onClick={handleSubmit}
        disabled={selectedReframings.size === 0}
        className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-200 disabled:text-gray-400 disabled:shadow-none disabled:cursor-not-allowed text-white font-semibold text-sm rounded-lg shadow-md shadow-indigo-200/50 hover:shadow-lg hover:shadow-indigo-300/50 transition-all inline-flex items-center justify-center gap-2"
      >
        {selectedReframings.size > 0
          ? t("decompose.submitReview")
          : t("decompose.submitReview")}
      </button>
    </div>
  );
};
