/* DecomposeReview — Phase 1 review UI with 2 section containers (Assumptions + Reframings).

Invariants:
    - All assumptions start pending (user must select a dynamic option or add argument)
    - At least 1 reframing must resonate (option > 0), have custom argument, or be selected
    - Carousel allows free navigation (prev/next) through assumptions and reframings
    - Option selection auto-advances to next card after brief visual feedback
    - "Add your argument" replaces "Add new item" — enriches existing cards, not new entities

Design Decisions:
    - Fundamentals hidden from UI but still sent as context to the model (ADR: reduce visual noise)
    - 2 containers: Assumptions, Reframings — gray left accent by default, green on completion
    - Carousel over list: reduces cognitive load when 3+ items (ADR: hackathon UX polish)
    - slideDirection state + key remount triggers CSS animation per direction
    - Auto-advance delay (300ms) lets user see the color feedback before slide
    - Dynamic options from model replace hardcoded Confirm/Reject (ADR: richer downstream context)
    - Reframing resonance: same pattern as analogy resonance (Phase 2) — carousel with
      resonance_prompt + graduated options. Option 0 = "no shift" (gray). Option 1+ = resonance (green).
    - Fallback to checkbox list when no resonance data (backward compat with old sessions)
    - Suggested domains section: user can suggest domains for Phase 2 exploration (moved from ExploreReview)
*/

import React, { useState, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import type { DecomposeReviewData, UserInput } from "../types";
import ClaimMarkdown from "./ClaimMarkdown";

interface DecomposeReviewProps {
  data: DecomposeReviewData;
  onSubmit: (input: UserInput) => void;
}

export const DecomposeReview: React.FC<DecomposeReviewProps> = ({ data, onSubmit }) => {
  const { t } = useTranslation();

  // -- Assumptions carousel state --
  const [assumptionResponses, setAssumptionResponses] = useState<Map<number, number>>(new Map());
  const [currentCard, setCurrentCard] = useState(0);
  const [slideDirection, setSlideDirection] = useState<"left" | "right">("right");
  const autoAdvanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [assumptionsDone, setAssumptionsDone] = useState(false);
  const [assumptionsCollapsed, setAssumptionsCollapsed] = useState(false);

  // -- Reframings state --
  const [reframingResponses, setReframingResponses] = useState<Map<number, number>>(new Map());
  const [currentReframingCard, setCurrentReframingCard] = useState(0);
  const [reframingSlideDirection, setReframingSlideDirection] = useState<"left" | "right">("right");
  const reframingAutoAdvanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const assumptionsCardRef = useRef<HTMLDivElement>(null);
  const reframingsCardRef = useRef<HTMLDivElement>(null);
  const [reframingsDone, setReframingsDone] = useState(false);
  const [reframingsCollapsed, setReframingsCollapsed] = useState(false);
  const [selectedReframings, setSelectedReframings] = useState<Set<number>>(new Set());

  // -- Custom argument state (per-card inline input) --
  const [customArgTexts, setCustomArgTexts] = useState<Map<number, string>>(new Map());
  const [customArgInput, setCustomArgInput] = useState<Map<number, string>>(new Map());
  const [showCustomArgInput, setShowCustomArgInput] = useState<Map<number, boolean>>(new Map());
  const [customRefTexts, setCustomRefTexts] = useState<Map<number, string>>(new Map());
  const [customRefInput, setCustomRefInput] = useState<Map<number, string>>(new Map());
  const [showCustomRefInput, setShowCustomRefInput] = useState<Map<number, boolean>>(new Map());

  // -- Suggested domains (moved from ExploreReview — useful pre-Phase 2) --
  const [suggestedDomains, setSuggestedDomains] = useState<string[]>([]);
  const [domainInput, setDomainInput] = useState("");

  // -- Helper to update Map state --
  function updateMap<K, V>(setter: React.Dispatch<React.SetStateAction<Map<K, V>>>, key: K, value: NoInfer<V>) {
    setter(prev => { const next = new Map(prev); next.set(key, value); return next; });
  }

  // -- Assumptions derived --
  const totalAssumptions = data.assumptions.length;
  const allAssumptionsReviewed = totalAssumptions > 0 && (assumptionResponses.size + customArgTexts.size) >= totalAssumptions;
  const isLastCard = currentCard >= totalAssumptions - 1;
  const isFirstCard = currentCard <= 0;

  // -- Reframings derived --
  const totalReframings = data.reframings.length;
  const hasResonanceData = data.reframings.some(r => r.resonance_options && r.resonance_options.length > 0);
  const allReframingsReviewed = totalReframings > 0 && (reframingResponses.size + customRefTexts.size) >= totalReframings;
  const hasResonanceSelection = Array.from(reframingResponses.values()).some(opt => opt > 0) || customRefTexts.size > 0;
  const isLastReframingCard = currentReframingCard >= totalReframings - 1;
  const isFirstReframingCard = currentReframingCard <= 0;

  // -- Assumptions carousel navigation --
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

    // Clear any custom argument for this card if selecting a predefined option
    setCustomArgTexts(prev => { const next = new Map(prev); next.delete(assumptionIndex); return next; });

    setAssumptionResponses((prev) => {
      const next = new Map(prev);
      if (next.get(assumptionIndex) === optionIndex) {
        next.delete(assumptionIndex);
      } else {
        next.set(assumptionIndex, optionIndex);
      }

      const totalAnswered = next.size + customArgTexts.size;
      if (totalAnswered >= totalAssumptions) {
        autoAdvanceTimer.current = setTimeout(() => {
          setAssumptionsDone(true);
          setAssumptionsCollapsed(true);
        }, 400);
      } else if (assumptionIndex < totalAssumptions - 1) {
        autoAdvanceTimer.current = setTimeout(() => goNext(), 300);
      }

      return next;
    });
    assumptionsCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [totalAssumptions, goNext, customArgTexts.size]);

  // -- Custom argument submission for assumptions --
  const submitCustomArg = useCallback((cardIndex: number) => {
    const text = (customArgInput.get(cardIndex) || "").trim();
    if (!text) return;
    updateMap(setCustomArgTexts, cardIndex, text);
    // Set selected_option to options.length (beyond predefined)
    const optCount = data.assumptions[cardIndex]?.options?.length ?? 2;
    setAssumptionResponses(prev => { const next = new Map(prev); next.set(cardIndex, optCount); return next; });
    updateMap(setShowCustomArgInput, cardIndex, false);
    // Auto-advance
    const totalAnswered = assumptionResponses.size + customArgTexts.size + 1;
    if (totalAnswered >= totalAssumptions) {
      setTimeout(() => { setAssumptionsDone(true); setAssumptionsCollapsed(true); }, 400);
    } else if (cardIndex < totalAssumptions - 1) {
      setTimeout(() => goNext(), 300);
    }
  }, [customArgInput, data.assumptions, assumptionResponses.size, customArgTexts.size, totalAssumptions, goNext]);

  // -- Reframings carousel navigation --
  const goToReframingCard = useCallback((index: number, direction: "left" | "right") => {
    if (index < 0 || index >= totalReframings) return;
    setReframingSlideDirection(direction);
    setCurrentReframingCard(index);
  }, [totalReframings]);

  const goNextReframing = useCallback(() => {
    if (!isLastReframingCard) goToReframingCard(currentReframingCard + 1, "right");
  }, [currentReframingCard, isLastReframingCard, goToReframingCard]);

  const goPrevReframing = useCallback(() => {
    if (!isFirstReframingCard) goToReframingCard(currentReframingCard - 1, "left");
  }, [currentReframingCard, isFirstReframingCard, goToReframingCard]);

  const selectReframingOption = useCallback((reframingIndex: number, optionIndex: number) => {
    if (reframingAutoAdvanceTimer.current) clearTimeout(reframingAutoAdvanceTimer.current);

    // Clear custom argument if selecting a predefined option
    setCustomRefTexts(prev => { const next = new Map(prev); next.delete(reframingIndex); return next; });

    setReframingResponses((prev) => {
      const next = new Map(prev);
      if (next.get(reframingIndex) === optionIndex) {
        next.delete(reframingIndex);
      } else {
        next.set(reframingIndex, optionIndex);
      }

      const totalAnswered = next.size + customRefTexts.size;
      if (totalAnswered >= totalReframings) {
        reframingAutoAdvanceTimer.current = setTimeout(() => {
          setReframingsDone(true);
          setReframingsCollapsed(true);
        }, 400);
      } else if (reframingIndex < totalReframings - 1) {
        reframingAutoAdvanceTimer.current = setTimeout(() => goNextReframing(), 300);
      }

      return next;
    });
    reframingsCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [totalReframings, goNextReframing, customRefTexts.size]);

  // -- Custom argument submission for reframings --
  const submitCustomRef = useCallback((cardIndex: number) => {
    const text = (customRefInput.get(cardIndex) || "").trim();
    if (!text) return;
    updateMap(setCustomRefTexts, cardIndex, text);
    const optCount = data.reframings[cardIndex]?.resonance_options?.length ?? 2;
    setReframingResponses(prev => { const next = new Map(prev); next.set(cardIndex, optCount); return next; });
    updateMap(setShowCustomRefInput, cardIndex, false);
    const totalAnswered = reframingResponses.size + customRefTexts.size + 1;
    if (totalAnswered >= totalReframings) {
      setTimeout(() => { setReframingsDone(true); setReframingsCollapsed(true); }, 400);
    } else if (cardIndex < totalReframings - 1) {
      setTimeout(() => goNextReframing(), 300);
    }
  }, [customRefInput, data.reframings, reframingResponses.size, customRefTexts.size, totalReframings, goNextReframing]);

  // -- Checkbox fallback toggle --
  const toggleReframing = (index: number) => {
    setSelectedReframings((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index); else next.add(index);
      return next;
    });
    reframingsCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  // -- Domain suggestion handlers --
  const addDomain = () => {
    const text = domainInput.trim();
    if (!text) return;
    setSuggestedDomains(prev => [...prev, text]);
    setDomainInput("");
  };
  const removeDomain = (index: number) => {
    setSuggestedDomains(prev => prev.filter((_, i) => i !== index));
  };

  // -- Submit --
  const handleSubmit = () => {
    const input: UserInput = {
      type: "decompose_review",
      assumption_responses: Array.from(assumptionResponses.entries()).map(
        ([idx, opt]) => {
          const resp: { assumption_index: number; selected_option: number; custom_argument?: string } = {
            assumption_index: idx, selected_option: opt,
          };
          const custom = customArgTexts.get(idx);
          if (custom) resp.custom_argument = custom;
          return resp;
        },
      ),
      suggested_domains: suggestedDomains.length > 0 ? suggestedDomains : undefined,
    };
    if (hasResonanceData) {
      input.reframing_responses = Array.from(reframingResponses.entries()).map(
        ([idx, opt]) => {
          const resp: { reframing_index: number; selected_option: number; custom_argument?: string } = {
            reframing_index: idx, selected_option: opt,
          };
          const custom = customRefTexts.get(idx);
          if (custom) resp.custom_argument = custom;
          return resp;
        },
      );
    } else {
      input.selected_reframings = Array.from(selectedReframings);
    }
    onSubmit(input);
  };

  // -- Can submit? --
  const canSubmit = hasResonanceData ? hasResonanceSelection : selectedReframings.size > 0;

  const isReviewed = (index: number): boolean => assumptionResponses.has(index) || customArgTexts.has(index);
  const isReframingReviewed = (index: number): boolean => reframingResponses.has(index) || customRefTexts.has(index);

  const assumption = data.assumptions[currentCard];
  const reframing = data.reframings[currentReframingCard];

  const animationClass =
    slideDirection === "right" ? "animate-slide-in-right" : "animate-slide-in-left";
  const reframingAnimationClass =
    reframingSlideDirection === "right" ? "animate-slide-in-right" : "animate-slide-in-left";

  return (
    <div className="space-y-4">
      {/* -- Assumptions -- */}
      {assumptionsCollapsed ? (
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
        <div ref={assumptionsCardRef} className={`scroll-mt-4 bg-white border border-gray-200/80 border-l-4 rounded-xl shadow-sm p-5 transition-all ${
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

                <div
                  key={currentCard}
                  className={`flex-1 p-5 rounded-lg text-center ${animationClass}`}
                >
                  <p className="text-xs text-gray-400 font-medium mb-2">
                    {currentCard + 1} / {totalAssumptions}
                  </p>
                  <ClaimMarkdown className="text-gray-700 text-sm leading-relaxed mb-4">
                    {assumption.text}
                  </ClaimMarkdown>
                  {assumption.options && assumption.options.length > 0 ? (
                    <div className="flex flex-col gap-2">
                      {assumption.options.map((option, optIdx) => {
                        const selected = assumptionResponses.get(currentCard) === optIdx && !customArgTexts.has(currentCard);
                        return (
                          <button
                            key={optIdx}
                            onClick={() => selectOption(currentCard, optIdx)}
                            className={`w-full px-4 py-2 rounded-md text-xs font-medium transition-all text-left ${
                              selected
                                ? "bg-green-500 text-white"
                                : "bg-white border border-gray-200 text-gray-600 hover:border-green-300 hover:text-green-600"
                            }`}
                          >
                            {option}
                          </button>
                        );
                      })}

                      {/* Custom argument display or input */}
                      {customArgTexts.has(currentCard) ? (
                        <button
                          onClick={() => {
                            setCustomArgTexts(prev => { const next = new Map(prev); next.delete(currentCard); return next; });
                            updateMap(setShowCustomArgInput, currentCard, true);
                            updateMap(setCustomArgInput, currentCard, customArgTexts.get(currentCard) || "");
                          }}
                          className="w-full px-4 py-2 rounded-md text-xs font-medium transition-all text-left bg-green-500 text-white"
                        >
                          {customArgTexts.get(currentCard)}
                        </button>
                      ) : showCustomArgInput.get(currentCard) ? (
                        <div className="flex items-center gap-2">
                          <input
                            autoFocus
                            type="text"
                            value={customArgInput.get(currentCard) || ""}
                            onChange={e => updateMap(setCustomArgInput, currentCard, e.target.value)}
                            onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); submitCustomArg(currentCard); } }}
                            onBlur={() => submitCustomArg(currentCard)}
                            placeholder={t("common.addYourArgument")}
                            className="flex-1 px-3 py-1.5 text-xs border border-dashed border-gray-300 rounded-md bg-white text-gray-700 placeholder-gray-400 focus:outline-none focus:border-green-400"
                          />
                        </div>
                      ) : (
                        <button
                          onClick={() => updateMap(setShowCustomArgInput, currentCard, true)}
                          className="w-full px-4 py-2 rounded-md text-xs font-medium transition-all text-left text-gray-400 hover:text-green-600 border border-dashed border-gray-300 hover:border-green-300"
                        >
                          + {t("common.addYourArgument")}
                        </button>
                      )}
                    </div>
                  ) : (
                    <div className="flex justify-center gap-3">
                      <button
                        onClick={() => selectOption(currentCard, 0)}
                        className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-all inline-flex items-center gap-1.5 ${
                          assumptionResponses.get(currentCard) === 0
                            ? "bg-green-500 text-white"
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
                            ? "bg-green-400 text-white"
                            : "bg-white border border-gray-200 text-gray-600 hover:border-green-300 hover:text-green-600"
                        }`}
                      >
                        <i className="bi bi-x-lg" />
                        {t("decompose.reject")}
                      </button>
                    </div>
                  )}
                </div>

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
        </div>
      )}

      {/* -- Reframings (appears after all assumptions reviewed) -- */}
      {allAssumptionsReviewed && (
        <>
          {reframingsCollapsed ? (
            /* Collapsed green summary — click to re-expand */
            <div
              onClick={() => { setReframingsCollapsed(false); setReframingsDone(false); }}
              className="bg-white border border-gray-200/80 border-l-4 border-l-green-500 rounded-xl shadow-sm p-4 cursor-pointer hover:bg-green-50/30 transition-colors animate-fade-in"
            >
              <div className="flex items-center gap-2.5">
                <i className="bi bi-patch-check-fill text-green-500 text-base" />
                <span className="text-sm font-semibold text-green-600 uppercase tracking-wide flex-1">
                  {t("decompose.reframings")} ({totalReframings}/{totalReframings})
                </span>
                <span className="text-xs text-gray-400 flex items-center gap-1">
                  <i className="bi bi-pencil text-[10px]" />
                  {t("decompose.edit")}
                </span>
              </div>
            </div>
          ) : hasResonanceData ? (
            /* Resonance carousel — mirrors analogy carousel from Phase 2 */
            <div ref={reframingsCardRef} className={`scroll-mt-4 bg-white border border-gray-200/80 border-l-4 rounded-xl shadow-sm p-5 animate-fade-in ${
              hasResonanceSelection ? "border-l-green-500" : "border-l-gray-300"
            } ${reframingsDone ? "animate-fade-in" : ""}`}>
              <h3 className={`flex items-center gap-2.5 text-sm font-semibold uppercase tracking-wide mb-4 ${
                hasResonanceSelection ? "text-green-600" : "text-gray-400"
              }`}>
                <i className="bi bi-shuffle text-base" />
                {t("decompose.reframings")}
                {allReframingsReviewed && (
                  <span className="ml-auto text-xs text-green-500 font-normal flex items-center gap-1">
                    <i className="bi bi-check-circle-fill text-[11px]" />
                  </span>
                )}
              </h3>

              {totalReframings > 0 && reframing && (
                <div className="flex flex-col items-center">
                  {/* Progress dots */}
                  <div className="flex items-center gap-1.5 mb-4">
                    {data.reframings.map((_, i) => {
                      const reviewed = isReframingReviewed(i);
                      const responded = reframingResponses.get(i);
                      const dotColor = reviewed
                        ? (responded !== undefined && responded > 0 ? "bg-green-500" : customRefTexts.has(i) ? "bg-green-500" : "bg-gray-400")
                        : "bg-gray-300";
                      const ring = i === currentReframingCard ? "ring-2 ring-green-400 ring-offset-1" : "";
                      return (
                        <button
                          key={i}
                          onClick={() => goToReframingCard(i, i > currentReframingCard ? "right" : "left")}
                          className={`w-2.5 h-2.5 rounded-full transition-all ${dotColor} ${ring}`}
                          aria-label={`Reframing ${i + 1}`}
                        />
                      );
                    })}
                  </div>

                  {/* Card + navigation */}
                  <div className="flex items-center gap-3 w-full max-w-lg">
                    <button
                      onClick={goPrevReframing}
                      disabled={isFirstReframingCard}
                      className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
                        isFirstReframingCard
                          ? "text-gray-300 cursor-not-allowed"
                          : "text-gray-500 hover:bg-green-50 hover:text-green-600"
                      }`}
                      aria-label="Previous reframing"
                    >
                      <i className="bi bi-chevron-left text-lg" />
                    </button>

                    <div
                      key={currentReframingCard}
                      className={`flex-1 p-5 rounded-lg text-center ${reframingAnimationClass}`}
                    >
                      <p className="text-xs text-gray-400 font-medium mb-2">
                        {currentReframingCard + 1} / {totalReframings}
                      </p>
                      <div className="text-left max-w-md mx-auto mb-2">
                        <ClaimMarkdown className="text-gray-700 text-sm leading-relaxed">
                          {reframing.text}
                        </ClaimMarkdown>
                        {reframing.reasoning && (
                          <ClaimMarkdown className="text-xs text-gray-400 italic mt-2">
                            {reframing.reasoning}
                          </ClaimMarkdown>
                        )}
                      </div>

                      {/* Resonance prompt */}
                      {reframing.resonance_prompt && (
                        <div className="text-left max-w-md mx-auto mb-4">
                          <ClaimMarkdown className="text-gray-500 text-sm italic font-medium">
                            {reframing.resonance_prompt}
                          </ClaimMarkdown>
                        </div>
                      )}

                      {/* Resonance option buttons */}
                      {reframing.resonance_options && reframing.resonance_options.length > 0 && (
                        <div className="flex flex-col gap-2">
                          {reframing.resonance_options.map((option, optIdx) => {
                            const selected = reframingResponses.get(currentReframingCard) === optIdx && !customRefTexts.has(currentReframingCard);
                            return (
                              <button
                                key={optIdx}
                                onClick={() => selectReframingOption(currentReframingCard, optIdx)}
                                className={`w-full px-4 py-2 rounded-md text-xs font-medium transition-all text-left ${
                                  selected
                                    ? optIdx === 0
                                      ? "bg-gray-400 text-white"
                                      : "bg-green-500 text-white"
                                    : optIdx === 0
                                      ? "bg-white border border-gray-300 text-gray-500 hover:border-gray-400"
                                      : "bg-white border border-gray-200 text-gray-600 hover:border-green-300 hover:text-green-600"
                                }`}
                              >
                                {option}
                              </button>
                            );
                          })}

                          {/* Custom argument for reframing */}
                          {customRefTexts.has(currentReframingCard) ? (
                            <button
                              onClick={() => {
                                setCustomRefTexts(prev => { const next = new Map(prev); next.delete(currentReframingCard); return next; });
                                updateMap(setShowCustomRefInput, currentReframingCard, true);
                                updateMap(setCustomRefInput, currentReframingCard, customRefTexts.get(currentReframingCard) || "");
                              }}
                              className="w-full px-4 py-2 rounded-md text-xs font-medium transition-all text-left bg-green-500 text-white"
                            >
                              {customRefTexts.get(currentReframingCard)}
                            </button>
                          ) : showCustomRefInput.get(currentReframingCard) ? (
                            <div className="flex items-center gap-2">
                              <input
                                autoFocus
                                type="text"
                                value={customRefInput.get(currentReframingCard) || ""}
                                onChange={e => updateMap(setCustomRefInput, currentReframingCard, e.target.value)}
                                onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); submitCustomRef(currentReframingCard); } }}
                                onBlur={() => submitCustomRef(currentReframingCard)}
                                placeholder={t("common.addYourArgument")}
                                className="flex-1 px-3 py-1.5 text-xs border border-dashed border-gray-300 rounded-md bg-white text-gray-700 placeholder-gray-400 focus:outline-none focus:border-green-400"
                              />
                            </div>
                          ) : (
                            <button
                              onClick={() => updateMap(setShowCustomRefInput, currentReframingCard, true)}
                              className="w-full px-4 py-2 rounded-md text-xs font-medium transition-all text-left text-gray-400 hover:text-green-600 border border-dashed border-gray-300 hover:border-green-300"
                            >
                              + {t("common.addYourArgument")}
                            </button>
                          )}
                        </div>
                      )}
                    </div>

                    <button
                      onClick={goNextReframing}
                      disabled={isLastReframingCard}
                      className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
                        isLastReframingCard
                          ? "text-gray-300 cursor-not-allowed"
                          : "text-gray-500 hover:bg-green-50 hover:text-green-600"
                      }`}
                      aria-label="Next reframing"
                    >
                      <i className="bi bi-chevron-right text-lg" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Checkbox fallback — backward compat with old sessions */
            <div ref={reframingsCardRef} className={`scroll-mt-4 bg-white border border-gray-200/80 border-l-4 rounded-xl shadow-sm p-5 animate-fade-in ${
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
                {data.reframings.map((r, i) => (
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
                      <ClaimMarkdown className="text-gray-700 text-sm">{r.text}</ClaimMarkdown>
                      <p className="text-xs text-gray-400 mt-1 inline-flex items-center gap-1">
                        <i className="bi bi-tag text-[10px]" />
                        {r.type}
                      </p>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* -- Suggested domains for Phase 2 -- */}
          <div className="bg-white border border-gray-200/80 border-l-4 border-l-blue-400 rounded-xl shadow-sm p-5 animate-fade-in">
            <h3 className="flex items-center gap-2.5 text-sm font-semibold text-blue-600 uppercase tracking-wide mb-2">
              <i className="bi bi-globe2 text-base" />
              {t("decompose.suggestDomain")}
            </h3>
            <p className="text-xs text-gray-500 leading-relaxed mb-3">
              {t("decompose.suggestDomainHint")}
            </p>
            {suggestedDomains.map((text, i) => (
              <div
                key={`domain-${i}`}
                className="group relative mb-2 p-3 rounded-lg border bg-blue-50 border-blue-200"
              >
                <span className="text-gray-700 text-sm font-medium pr-6">{text}</span>
                <button
                  onClick={() => removeDomain(i)}
                  className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-red-500"
                  aria-label="Remove"
                >
                  <i className="bi bi-x-lg text-xs" />
                </button>
              </div>
            ))}
            <div className="p-3 rounded-lg border border-dashed border-gray-300">
              <div className="flex items-center gap-2">
                <i className="bi bi-plus-lg text-gray-400 text-sm" />
                <input
                  type="text"
                  value={domainInput}
                  onChange={e => setDomainInput(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addDomain(); } }}
                  onBlur={() => addDomain()}
                  placeholder={t("decompose.suggestDomainPlaceholder")}
                  className="flex-1 bg-transparent text-gray-700 text-sm placeholder-gray-400 focus:outline-none"
                />
              </div>
            </div>
          </div>
        </>
      )}

      {/* -- Submit (only after assumptions reviewed) -- */}
      {allAssumptionsReviewed && (
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="w-full py-3 bg-green-600 hover:bg-green-500 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-lg transition-all inline-flex items-center justify-center gap-2 animate-fade-in"
        >
          {t("decompose.submitReview")}
        </button>
      )}
    </div>
  );
};
