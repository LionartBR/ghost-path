/* GapCarousel — Phase 5 gap triage with select/reject actions and auto-advance.

Invariants:
    - Each gap must be explicitly triaged: "investigate" or "reject"
    - Auto-advances to next unreviewed gap after action (300ms)
    - Auto-collapses into summary bar when all gaps are triaged (400ms)
    - Collapsed summary is clickable to re-expand
    - Only "investigate" indices are sent on submit — rejected gaps are omitted
    - CTA disabled when zero gaps selected for investigation

Design Decisions:
    - Two stacked buttons per gap over single toggle: explicit intent, no ambiguity (ADR: UX clarity)
    - GAP_ACTION_META lookup table: mirrors VerdictPanel VERDICT_META pattern for consistency
    - Semantic dots (green/red/gray): at-a-glance triage distribution, same as VerdictPanel
    - Auto-advance wraps around to find next unreviewed: avoids dead-end at last card
*/

import { useState, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import ClaimMarkdown from "./ClaimMarkdown";

type GapAction = "investigate" | "reject";

interface GapCarouselProps {
  gaps: string[];
  onInvestigate: (selectedIndices: number[]) => void;
}

const GAP_ACTION_META: Record<GapAction, { key: string; dot: string; active: string; inactive: string }> = {
  investigate: {
    key: "build.selectForInvestigation", dot: "bg-green-500",
    active: "bg-green-600 text-white",
    inactive: "bg-white border border-gray-200 text-gray-600 hover:border-green-300 hover:text-green-600",
  },
  reject: {
    key: "build.rejectGap", dot: "bg-red-400",
    active: "bg-red-400 text-white",
    inactive: "bg-white border border-gray-200 text-gray-600 hover:border-red-300 hover:text-red-400",
  },
};

const GAP_ACTIONS: GapAction[] = ["investigate", "reject"];

export default function GapCarousel({ gaps, onInvestigate }: GapCarouselProps) {
  const { t } = useTranslation();
  const totalGaps = gaps.length;

  const [gapActions, setGapActions] = useState<Map<number, GapAction>>(new Map());
  const [currentCard, setCurrentCard] = useState(0);
  const [slideDirection, setSlideDirection] = useState<"left" | "right">("right");
  const [collapsed, setCollapsed] = useState(false);
  const autoAdvanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* Derived values */
  const selectedIndices = [...gapActions.entries()].filter(([, a]) => a === "investigate").map(([i]) => i);
  const rejectedCount = [...gapActions.values()].filter((a) => a === "reject").length;
  const allTriaged = totalGaps > 0 && gapActions.size >= totalGaps;

  const isFirstCard = currentCard <= 0;
  const isLastCard = currentCard >= totalGaps - 1;

  const goToCard = useCallback((index: number, direction: "left" | "right") => {
    if (index < 0 || index >= totalGaps) return;
    setSlideDirection(direction);
    setCurrentCard(index);
  }, [totalGaps]);

  const goNext = useCallback(() => {
    if (!isLastCard) goToCard(currentCard + 1, "right");
  }, [currentCard, isLastCard, goToCard]);

  const goPrev = useCallback(() => {
    if (!isFirstCard) goToCard(currentCard - 1, "left");
  }, [currentCard, isFirstCard, goToCard]);

  /* Find next unreviewed gap (wrap-around) */
  const findNextUnreviewed = useCallback((afterIndex: number, updatedActions: Map<number, GapAction>): number | null => {
    for (let offset = 1; offset < totalGaps; offset++) {
      const candidate = (afterIndex + offset) % totalGaps;
      if (!updatedActions.has(candidate)) return candidate;
    }
    return null;
  }, [totalGaps]);

  const setAction = useCallback((index: number, action: GapAction) => {
    if (autoAdvanceTimer.current) clearTimeout(autoAdvanceTimer.current);
    setGapActions((prev) => {
      const updated = new Map(prev);
      updated.set(index, action);
      const nextUnreviewed = findNextUnreviewed(index, updated);
      if (nextUnreviewed === null) {
        /* All triaged → auto-collapse */
        autoAdvanceTimer.current = setTimeout(() => setCollapsed(true), 400);
      } else {
        /* Auto-advance to next unreviewed */
        const direction = nextUnreviewed > index ? "right" : "left";
        autoAdvanceTimer.current = setTimeout(() => goToCard(nextUnreviewed, direction), 300);
      }
      return updated;
    });
  }, [findNextUnreviewed, goToCard]);

  if (totalGaps === 0) return null;

  const handleSubmit = () => {
    onInvestigate(selectedIndices);
  };

  const animationClass = slideDirection === "right" ? "animate-slide-in-right" : "animate-slide-in-left";
  const currentAction = gapActions.get(currentCard);

  /* Collapsed summary bar */
  if (collapsed) {
    return (
      <div
        onClick={() => setCollapsed(false)}
        className="bg-white border border-gray-200/80 border-l-4 border-l-green-500 rounded-xl shadow-sm p-4 cursor-pointer hover:bg-green-50/30 transition-colors animate-fade-in"
        data-testid="gap-collapsed-summary"
      >
        <div className="flex items-center gap-2.5">
          <i className="bi bi-lightning-fill text-green-500 text-base" />
          <span className="text-sm font-semibold text-green-600 uppercase tracking-wide flex-1">
            {t("build.gaps")} ({totalGaps}/{totalGaps})
          </span>
          <span className="text-xs text-gray-500">
            {t("build.gapSummary", { selected: selectedIndices.length, rejected: rejectedCount })}
          </span>
          <span className="text-xs text-gray-400 flex items-center gap-1">
            <i className="bi bi-pencil text-[10px]" /> {t("claims.edit")}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white border border-gray-200/80 border-l-4 rounded-xl shadow-sm p-5 transition-all ${
      selectedIndices.length > 0 ? "border-l-green-500" : "border-l-gray-300"
    }`}>
      <h3 className={`flex items-center gap-2.5 text-sm font-semibold uppercase tracking-wide mb-4 ${
        allTriaged ? "text-green-600" : "text-gray-400"
      }`}>
        <i className="bi bi-lightning text-base" />
        {t("build.gaps")}
        {allTriaged && (
          <span className="ml-auto text-xs text-green-500 font-normal flex items-center gap-1">
            <i className="bi bi-check-circle-fill text-[11px]" />
          </span>
        )}
      </h3>

      <div className="flex flex-col items-center">
        {/* Semantic dots — green (investigate), red (reject), gray (unreviewed) */}
        <div className="flex items-center gap-1.5 mb-4" data-testid="gap-dots">
          {gaps.map((_, i) => {
            const action = gapActions.get(i);
            const dotColor = action ? GAP_ACTION_META[action].dot : "bg-gray-300";
            const ring = i === currentCard ? "ring-2 ring-green-400 ring-offset-1" : "";
            return (
              <button
                key={i}
                onClick={() => goToCard(i, i > currentCard ? "right" : "left")}
                className={`w-2.5 h-2.5 rounded-full transition-all ${dotColor} ${ring}`}
                aria-label={`Gap ${i + 1}`}
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
              isFirstCard ? "text-gray-300 cursor-not-allowed" : "text-gray-500 hover:bg-green-50 hover:text-green-600"
            }`}
            aria-label="Previous gap"
          >
            <i className="bi bi-chevron-left text-lg" />
          </button>

          <div key={currentCard} className={`flex-1 p-5 rounded-lg text-center ${animationClass}`}>
            <p className="text-xs text-gray-400 font-medium mb-2">{currentCard + 1} / {totalGaps}</p>
            <div className="text-left max-w-md mx-auto mb-4">
              <ClaimMarkdown className="text-sm text-gray-700 leading-relaxed">{gaps[currentCard]}</ClaimMarkdown>
            </div>
            {/* Two action buttons — stacked full-width */}
            <div className="flex flex-col gap-2">
              {GAP_ACTIONS.map((action) => {
                const meta = GAP_ACTION_META[action];
                return (
                  <button
                    key={action}
                    onClick={() => setAction(currentCard, action)}
                    className={`w-full py-2.5 px-4 rounded-md font-medium text-sm transition-all text-left ${
                      currentAction === action ? meta.active : meta.inactive
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <i className={`bi ${currentAction === action ? "bi-check-circle-fill" : "bi-circle"} text-sm`} />
                      {t(meta.key)}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <button
            onClick={goNext}
            disabled={isLastCard}
            className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
              isLastCard ? "text-gray-300 cursor-not-allowed" : "text-gray-500 hover:bg-green-50 hover:text-green-600"
            }`}
            aria-label="Next gap"
          >
            <i className="bi bi-chevron-right text-lg" />
          </button>
        </div>
      </div>

      {/* CTA: Investigate selected */}
      <button
        onClick={handleSubmit}
        disabled={selectedIndices.length === 0}
        className="w-full mt-4 bg-green-600 hover:bg-green-500 text-white font-semibold text-sm py-3 px-6 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {t("build.investigateSelected", { count: selectedIndices.length })}
      </button>
    </div>
  );
}
