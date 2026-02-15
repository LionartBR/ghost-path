/* ExploreReview — Phase 2 review UI with carousel for analogy resonance assessment.

Invariants:
    - At least 1 analogy must resonate (selected_option > 0) or have custom argument before submit
    - Carousel reuses DecomposeReview pattern: progress dots, prev/next, auto-advance
    - Morphological box and contradictions are collapsible (read-only context)
    - Backward compat: falls back to simple star toggle when no resonance data
    - "Suggest domain" moved to DecomposeReview (pre-Phase 2, more useful there)

Design Decisions:
    - Convention Option 0: agent always generates option 0 as "no structural connection"
    - selected_option > 0 means the analogy resonated (replaces binary star toggle)
    - custom_argument enriches existing analogy card (not a new entity)
    - Resonance text injected into Phase 3 context for richer thesis generation
    - Carousel over grid: reduces cognitive load, matches DecomposeReview UX (ADR)
*/

import React, { useState, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import type { ExploreReviewData, UserInput } from "../types";
import ClaimMarkdown from "./ClaimMarkdown";

interface ExploreReviewProps {
  data: ExploreReviewData;
  onSubmit: (input: UserInput) => void;
}

export const ExploreReview: React.FC<ExploreReviewProps> = ({ data, onSubmit }) => {
  const { t } = useTranslation();
  const [morphBoxOpen, setMorphBoxOpen] = useState(false);
  const [contradictionsOpen, setContradictionsOpen] = useState(false);

  // Resonance carousel state (mirrors DecomposeReview pattern)
  const [analogyResponses, setAnalogyResponses] = useState<Map<number, number>>(new Map());
  const [currentCard, setCurrentCard] = useState(0);
  const [slideDirection, setSlideDirection] = useState<"left" | "right">("right");
  const autoAdvanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const analogiesCardRef = useRef<HTMLDivElement>(null);
  const [analogiesDone, setAnalogiesDone] = useState(false);
  const [analogiesCollapsed, setAnalogiesCollapsed] = useState(false);

  // Backward compat: star toggle for analogies without resonance data
  const [starredAnalogies, setStarredAnalogies] = useState<Set<number>>(new Set());

  // Custom argument state (per-analogy)
  const [customArgTexts, setCustomArgTexts] = useState<Map<number, string>>(new Map());
  const [customArgInput, setCustomArgInput] = useState<Map<number, string>>(new Map());
  const [showCustomArgInput, setShowCustomArgInput] = useState<Map<number, boolean>>(new Map());

  function updateMap<K, V>(setter: React.Dispatch<React.SetStateAction<Map<K, V>>>, key: K, value: NoInfer<V>) {
    setter(prev => { const next = new Map(prev); next.set(key, value); return next; });
  }

  const hasResonanceData = data.analogies.some(
    (a) => a.resonance_prompt && a.resonance_options && a.resonance_options.length >= 3,
  );

  const totalAnalogies = data.analogies.length;
  const allAnalogiesReviewed = totalAnalogies > 0 && (analogyResponses.size + customArgTexts.size) >= totalAnalogies;
  const isLastCard = currentCard >= totalAnalogies - 1;
  const isFirstCard = currentCard <= 0;

  const goToCard = useCallback((index: number, direction: "left" | "right") => {
    if (index < 0 || index >= totalAnalogies) return;
    setSlideDirection(direction);
    setCurrentCard(index);
  }, [totalAnalogies]);

  const goNext = useCallback(() => {
    if (!isLastCard) goToCard(currentCard + 1, "right");
  }, [currentCard, isLastCard, goToCard]);

  const goPrev = useCallback(() => {
    if (!isFirstCard) goToCard(currentCard - 1, "left");
  }, [currentCard, isFirstCard, goToCard]);

  const selectOption = useCallback((analogyIndex: number, optionIndex: number) => {
    if (autoAdvanceTimer.current) clearTimeout(autoAdvanceTimer.current);

    // Clear custom argument when selecting predefined option
    setCustomArgTexts(prev => { const next = new Map(prev); next.delete(analogyIndex); return next; });

    setAnalogyResponses((prev) => {
      const next = new Map(prev);
      if (next.get(analogyIndex) === optionIndex) {
        next.delete(analogyIndex);
      } else {
        next.set(analogyIndex, optionIndex);
      }

      const totalAnswered = next.size + customArgTexts.size;
      if (totalAnswered >= totalAnalogies) {
        autoAdvanceTimer.current = setTimeout(() => {
          setAnalogiesDone(true);
          setAnalogiesCollapsed(true);
        }, 400);
      } else if (analogyIndex < totalAnalogies - 1) {
        autoAdvanceTimer.current = setTimeout(() => goNext(), 300);
      }

      return next;
    });
    analogiesCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [totalAnalogies, goNext, customArgTexts.size]);

  // Custom argument submission for analogies
  const submitCustomArg = useCallback((cardIndex: number) => {
    const text = (customArgInput.get(cardIndex) || "").trim();
    if (!text) return;
    updateMap(setCustomArgTexts, cardIndex, text);
    const optCount = data.analogies[cardIndex]?.resonance_options?.length ?? 2;
    setAnalogyResponses(prev => { const next = new Map(prev); next.set(cardIndex, optCount); return next; });
    updateMap(setShowCustomArgInput, cardIndex, false);
    const totalAnswered = analogyResponses.size + customArgTexts.size + 1;
    if (totalAnswered >= totalAnalogies) {
      setTimeout(() => { setAnalogiesDone(true); setAnalogiesCollapsed(true); }, 400);
    } else if (cardIndex < totalAnalogies - 1) {
      setTimeout(() => goNext(), 300);
    }
  }, [customArgInput, data.analogies, analogyResponses.size, customArgTexts.size, totalAnalogies, goNext]);

  const toggleStar = (index: number) => {
    setStarredAnalogies((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index); else next.add(index);
      return next;
    });
    analogiesCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const resonatedCount = Array.from(analogyResponses.values()).filter((opt) => opt > 0).length;
  const canSubmit = hasResonanceData ? (resonatedCount > 0 || customArgTexts.size > 0) : starredAnalogies.size > 0;

  const handleSubmit = () => {
    if (hasResonanceData) {
      const input: UserInput = {
        type: "explore_review",
        analogy_responses: Array.from(analogyResponses.entries()).map(
          ([idx, opt]) => {
            const resp: { analogy_index: number; selected_option: number; custom_argument?: string } = {
              analogy_index: idx, selected_option: opt,
            };
            const custom = customArgTexts.get(idx);
            if (custom) resp.custom_argument = custom;
            return resp;
          },
        ),
      };
      onSubmit(input);
    } else {
      const input: UserInput = {
        type: "explore_review",
        starred_analogies: Array.from(starredAnalogies),
      };
      onSubmit(input);
    }
  };

  const analogy = data.analogies[currentCard];
  const animationClass =
    slideDirection === "right" ? "animate-slide-in-right" : "animate-slide-in-left";

  return (
    <div className="space-y-4">

      {/* -- Analogies -- */}
      {analogiesCollapsed ? (
        <div
          onClick={() => { setAnalogiesCollapsed(false); setAnalogiesDone(false); }}
          className="bg-white border border-gray-200/80 border-l-4 border-l-green-500 rounded-xl shadow-sm p-4 cursor-pointer hover:bg-green-50/30 transition-colors animate-fade-in"
        >
          <div className="flex items-center gap-2.5">
            <i className="bi bi-patch-check-fill text-green-500 text-base" />
            <span className="text-sm font-semibold text-green-600 uppercase tracking-wide flex-1">
              {t("explore.analogies")} ({totalAnalogies}/{totalAnalogies})
            </span>
            <span className="text-xs text-gray-400 flex items-center gap-1">
              <i className="bi bi-pencil text-[10px]" />
              {t("decompose.edit")}
            </span>
          </div>
        </div>
      ) : (
      <div ref={analogiesCardRef} className={`scroll-mt-4 bg-white border border-gray-200/80 border-l-4 rounded-xl shadow-sm p-5 transition-all ${
        resonatedCount > 0 || customArgTexts.size > 0 ? "border-l-green-500" : "border-l-gray-300"
      } ${analogiesDone ? "animate-fade-in" : ""}`}>
        <h3 className={`flex items-center gap-2.5 text-sm font-semibold uppercase tracking-wide mb-4 ${
          resonatedCount > 0 || customArgTexts.size > 0 ? "text-green-600" : "text-gray-400"
        }`}>
          <i className="bi bi-globe2 text-base" />
          {t("explore.analogies")}
          {allAnalogiesReviewed && (
            <span className="ml-auto text-xs text-green-500 font-normal flex items-center gap-1">
              <i className="bi bi-check-circle-fill text-[11px]" />
            </span>
          )}
        </h3>

        {hasResonanceData && totalAnalogies > 0 && analogy ? (
          /* -- Carousel mode (with resonance data) -- */
          <div className="flex flex-col items-center">
            {/* Progress dots */}
            <div className="flex items-center gap-1.5 mb-4">
              {data.analogies.map((_, i) => {
                const responded = analogyResponses.has(i);
                const resonated = (analogyResponses.get(i) ?? 0) > 0;
                const dotColor = resonated || customArgTexts.has(i)
                  ? "bg-green-500"
                  : responded
                    ? "bg-gray-400"
                    : "bg-gray-300";
                const ring = i === currentCard ? "ring-2 ring-green-400 ring-offset-1" : "";
                return (
                  <button
                    key={i}
                    onClick={() => goToCard(i, i > currentCard ? "right" : "left")}
                    className={`w-2.5 h-2.5 rounded-full transition-all ${dotColor} ${ring}`}
                    aria-label={`Analogy ${i + 1}`}
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
                aria-label="Previous analogy"
              >
                <i className="bi bi-chevron-left text-lg" />
              </button>

              {/* Card */}
              <div
                key={currentCard}
                className={`flex-1 p-5 rounded-lg text-center ${animationClass}`}
              >
                <p className="text-xs text-gray-400 font-medium mb-2">
                  {currentCard + 1} / {totalAnalogies}
                </p>

                <h4 className="font-semibold text-gray-900 text-sm mb-3">{analogy.domain}</h4>

                <div className="text-left max-w-md mx-auto mb-3">
                  {analogy.target_application && (
                    <ClaimMarkdown className="text-xs text-gray-400 mb-2">{analogy.target_application}</ClaimMarkdown>
                  )}
                  <ClaimMarkdown className="text-gray-600 text-sm leading-relaxed">
                    {analogy.description}
                  </ClaimMarkdown>
                </div>

                {/* Resonance prompt */}
                {analogy.resonance_prompt && (
                  <div className="text-left max-w-md mx-auto mb-4">
                    <ClaimMarkdown className="text-gray-500 text-sm italic">
                      {analogy.resonance_prompt}
                    </ClaimMarkdown>
                  </div>
                )}

                {/* Resonance option buttons */}
                {analogy.resonance_options && analogy.resonance_options.length > 0 && (
                  <div className="flex flex-col gap-2">
                    {analogy.resonance_options.map((option, optIdx) => {
                      const selected = analogyResponses.get(currentCard) === optIdx && !customArgTexts.has(currentCard);
                      return (
                        <button
                          key={optIdx}
                          onClick={() => selectOption(currentCard, optIdx)}
                          className={`w-full px-4 py-2 rounded-md text-xs font-medium transition-all text-left ${
                            selected
                              ? optIdx === 0
                                ? "bg-gray-400 text-white"
                                : "bg-green-500 text-white"
                              : "bg-white border border-gray-200 text-gray-600 hover:border-green-300 hover:text-green-600"
                          }`}
                        >
                          {option}
                        </button>
                      );
                    })}

                    {/* Custom argument for analogy */}
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
                aria-label="Next analogy"
              >
                <i className="bi bi-chevron-right text-lg" />
              </button>
            </div>
          </div>
        ) : (
          /* -- Grid mode (backward compat, no resonance data) -- */
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {data.analogies.map((a, i) => (
              <div
                key={i}
                className={`p-4 rounded-lg border transition-all ${
                  starredAnalogies.has(i)
                    ? "bg-green-50 border-green-300"
                    : "bg-gray-50 border-gray-200 hover:border-gray-300"
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-semibold text-gray-900 text-sm">{a.domain}</h4>
                  <button
                    onClick={() => toggleStar(i)}
                    className={`text-sm font-medium px-2 py-0.5 rounded transition-colors inline-flex items-center gap-1 ${
                      starredAnalogies.has(i)
                        ? "text-green-600 bg-green-100"
                        : "text-gray-400 hover:text-gray-600"
                    }`}
                  >
                    <i className={`bi ${starredAnalogies.has(i) ? "bi-star-fill" : "bi-star"}`} />
                    {starredAnalogies.has(i) ? t("explore.starred") : t("explore.star")}
                  </button>
                </div>
                <ClaimMarkdown className="text-gray-600 text-sm mb-2">{a.description}</ClaimMarkdown>
              </div>
            ))}
          </div>
        )}
      </div>
      )}

      {/* -- Morphological Box -- */}
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

      {/* -- Contradictions -- */}
      <div className="bg-white border border-gray-200/80 border-l-4 border-l-blue-400 rounded-xl shadow-sm p-5">
        <button
          onClick={() => setContradictionsOpen(!contradictionsOpen)}
          className="w-full flex items-center gap-2.5 text-sm font-semibold text-blue-600 uppercase tracking-wide hover:text-blue-500 transition-colors"
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
                  <span className="px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded text-xs font-medium">
                    {contradiction.property_a}
                  </span>
                  <i className="bi bi-arrow-left-right text-gray-400 text-xs" />
                  <span className="px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded text-xs font-medium">
                    {contradiction.property_b}
                  </span>
                </div>
                <ClaimMarkdown className="text-gray-600 text-sm">{contradiction.description}</ClaimMarkdown>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* -- Submit -- */}
      <button
        onClick={handleSubmit}
        disabled={!canSubmit}
        className="w-full py-3 bg-green-600 hover:bg-green-500 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-lg transition-all inline-flex items-center justify-center gap-2"
      >
        {canSubmit
          ? t("explore.submitReview", { count: hasResonanceData ? resonatedCount + customArgTexts.size : starredAnalogies.size })
          : t("explore.submitReviewNone")}
      </button>
    </div>
  );
};
