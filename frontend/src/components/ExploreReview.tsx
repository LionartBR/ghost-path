/* ExploreReview — Phase 2 review UI with carousel for analogy resonance assessment.

Invariants:
    - At least 1 analogy must resonate (selected_option > 0) before submit
    - Carousel reuses DecomposeReview pattern: progress dots, prev/next, auto-advance
    - Morphological box and contradictions are collapsible (read-only context)
    - Backward compat: falls back to simple star toggle when no resonance data

Design Decisions:
    - Convention Option 0: agent always generates option 0 as "no structural connection"
    - selected_option > 0 means the analogy resonated (replaces binary star toggle)
    - Resonance text injected into Phase 3 context for richer thesis generation
    - Carousel over grid: reduces cognitive load, matches DecomposeReview UX (ADR)
*/

import React, { useState, useCallback, useRef } from "react";
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
  const [newDomain, setNewDomain] = useState("");

  // Resonance carousel state (mirrors DecomposeReview pattern)
  const [analogyResponses, setAnalogyResponses] = useState<Map<number, number>>(new Map());
  const [currentCard, setCurrentCard] = useState(0);
  const [slideDirection, setSlideDirection] = useState<"left" | "right">("right");
  const autoAdvanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const analogiesCardRef = useRef<HTMLDivElement>(null);

  // Backward compat: star toggle for analogies without resonance data
  const [starredAnalogies, setStarredAnalogies] = useState<Set<number>>(new Set());

  const hasResonanceData = data.analogies.some(
    (a) => a.resonance_prompt && a.resonance_options && a.resonance_options.length >= 3,
  );

  const totalAnalogies = data.analogies.length;
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

    setAnalogyResponses((prev) => {
      const next = new Map(prev);
      if (next.get(analogyIndex) === optionIndex) {
        next.delete(analogyIndex);
      } else {
        next.set(analogyIndex, optionIndex);
      }
      return next;
    });
    analogiesCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });

    if (analogyIndex < totalAnalogies - 1) {
      autoAdvanceTimer.current = setTimeout(() => goNext(), 300);
    }
  }, [totalAnalogies, goNext]);

  const toggleStar = (index: number) => {
    setStarredAnalogies((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index); else next.add(index);
      return next;
    });
    analogiesCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const resonatedCount = Array.from(analogyResponses.values()).filter((opt) => opt > 0).length;
  const canSubmit = hasResonanceData ? resonatedCount > 0 : starredAnalogies.size > 0;

  const handleSubmit = () => {
    if (hasResonanceData) {
      const input: UserInput = {
        type: "explore_review",
        analogy_responses: Array.from(analogyResponses.entries()).map(
          ([idx, opt]) => ({ analogy_index: idx, selected_option: opt }),
        ),
        suggested_domains: newDomain.trim() ? [newDomain.trim()] : undefined,
      };
      onSubmit(input);
    } else {
      const input: UserInput = {
        type: "explore_review",
        starred_analogies: Array.from(starredAnalogies),
        suggested_domains: newDomain.trim() ? [newDomain.trim()] : undefined,
      };
      onSubmit(input);
    }
  };

  const analogy = data.analogies[currentCard];
  const animationClass =
    slideDirection === "right" ? "animate-slide-in-right" : "animate-slide-in-left";

  return (
    <div className="space-y-4">

      {/* ── Analogies ── */}
      <div ref={analogiesCardRef} className={`scroll-mt-4 bg-white border border-gray-200/80 border-l-4 rounded-xl shadow-sm p-5 transition-all ${
        resonatedCount > 0 ? "border-l-green-500" : "border-l-gray-300"
      }`}>
        <h3 className={`flex items-center gap-2.5 text-sm font-semibold uppercase tracking-wide mb-4 ${
          resonatedCount > 0 ? "text-green-600" : "text-gray-400"
        }`}>
          <i className="bi bi-globe2 text-base" />
          {t("explore.analogies")}
          {resonatedCount > 0 && (
            <span className="ml-auto text-xs text-green-500 font-normal flex items-center gap-1">
              <i className="bi bi-check-circle-fill text-[11px]" />
            </span>
          )}
        </h3>

        {hasResonanceData && totalAnalogies > 0 && analogy ? (
          /* ── Carousel mode (with resonance data) ── */
          <div className="flex flex-col items-center">
            {/* Progress dots */}
            <div className="flex items-center gap-1.5 mb-4">
              {data.analogies.map((_, i) => {
                const responded = analogyResponses.has(i);
                const resonated = (analogyResponses.get(i) ?? 0) > 0;
                const dotColor = resonated
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
                    <p className="text-xs text-gray-400 mb-2">{analogy.target_application}</p>
                  )}
                  <p className="text-gray-600 text-sm leading-relaxed">
                    {analogy.description}
                  </p>
                </div>

                {/* Resonance prompt */}
                {analogy.resonance_prompt && (
                  <div className="text-left max-w-md mx-auto mb-4">
                    <p className="text-gray-500 text-sm italic">
                      {analogy.resonance_prompt}
                    </p>
                  </div>
                )}

                {/* Resonance option buttons */}
                {analogy.resonance_options && analogy.resonance_options.length > 0 && (
                  <div className="flex flex-col gap-2">
                    {analogy.resonance_options.map((option, optIdx) => {
                      const selected = analogyResponses.get(currentCard) === optIdx;
                      return (
                        <button
                          key={optIdx}
                          onClick={() => selectOption(currentCard, optIdx)}
                          className={`w-full px-4 py-2 rounded-md text-xs font-medium transition-all text-left ${
                            selected
                              ? optIdx === 0
                                ? "bg-gray-400 text-white shadow-sm shadow-gray-200"
                                : "bg-green-500 text-white shadow-sm shadow-green-200"
                              : "bg-white border border-gray-200 text-gray-600 hover:border-green-300 hover:text-green-600"
                          }`}
                        >
                          {option}
                        </button>
                      );
                    })}
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
          /* ── Grid mode (backward compat, no resonance data) ── */
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
                <p className="text-gray-600 text-sm mb-2">{a.description}</p>
              </div>
            ))}
          </div>
        )}

        <input
          type="text"
          value={newDomain}
          onChange={(e) => setNewDomain(e.target.value)}
          placeholder={t("explore.suggestDomain")}
          className="mt-3 w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-gray-700 text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-400 focus:border-transparent"
        />
      </div>

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

      {/* ── Contradictions ── */}
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
                <p className="text-gray-600 text-sm">{contradiction.description}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Submit ── */}
      <button
        onClick={handleSubmit}
        disabled={!canSubmit}
        className="w-full py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-200 disabled:text-gray-400 disabled:shadow-none disabled:cursor-not-allowed text-white font-semibold text-sm rounded-lg shadow-md shadow-green-200/50 hover:shadow-lg hover:shadow-green-300/50 transition-all inline-flex items-center justify-center gap-2"
      >
        {canSubmit
          ? t("explore.submitReview", { count: hasResonanceData ? resonatedCount : starredAnalogies.size })
          : t("explore.submitReviewNone")}
      </button>
    </div>
  );
};
