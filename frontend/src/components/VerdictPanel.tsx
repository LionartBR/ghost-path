/* VerdictPanel — Phase 4 verdict UI with carousel navigation.

Invariants:
    - All claims default to "accept" if no explicit verdict set
    - Carousel allows free navigation (prev/next/dots) through claims
    - Verdict selection auto-advances to next card after brief visual feedback
    - Submit always available (unreviewed claims default to "accept")

Design Decisions:
    - Carousel over list: matches Phase 1 assumptions UX (ADR: consistent review pattern)
    - slideDirection state + key remount triggers CSS animation per direction
    - Auto-advance delay (300ms) lets user see the color feedback before slide
    - ClaimCard rendered compact inside carousel card for space efficiency
*/

import { useState, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import type { Claim, ClaimVerdict, UserInput, VerdictType } from "../types";
import ClaimCard from "./ClaimCard";

interface VerdictPanelProps {
  claims: Claim[];
  onSubmit: (input: UserInput) => void;
}

const VERDICT_STYLES: Record<VerdictType, { active: string; inactive: string }> = {
  accept: {
    active: "bg-emerald-600 text-white",
    inactive: "bg-white border border-gray-200 text-gray-600 hover:border-emerald-300 hover:text-emerald-600",
  },
  reject: {
    active: "bg-red-500 text-white",
    inactive: "bg-white border border-gray-200 text-gray-600 hover:border-red-300 hover:text-red-500",
  },
  qualify: {
    active: "bg-amber-500 text-white",
    inactive: "bg-white border border-gray-200 text-gray-600 hover:border-amber-300 hover:text-amber-600",
  },
  merge: {
    active: "bg-violet-500 text-white",
    inactive: "bg-white border border-gray-200 text-gray-600 hover:border-violet-300 hover:text-violet-600",
  },
};

const VERDICT_KEYS: Record<VerdictType, string> = {
  accept: "verdicts.accept",
  reject: "verdicts.reject",
  qualify: "verdicts.qualify",
  merge: "verdicts.merge",
};

export default function VerdictPanel({ claims, onSubmit }: VerdictPanelProps) {
  const { t } = useTranslation();
  const [verdicts, setVerdicts] = useState<Map<number, ClaimVerdict>>(new Map());

  const [currentCard, setCurrentCard] = useState(0);
  const [slideDirection, setSlideDirection] = useState<"left" | "right">("right");
  const autoAdvanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const carouselRef = useRef<HTMLDivElement>(null);

  const totalClaims = claims.length;
  const isLastCard = currentCard >= totalClaims - 1;
  const isFirstCard = currentCard <= 0;

  const goToCard = useCallback((index: number, direction: "left" | "right") => {
    if (index < 0 || index >= totalClaims) return;
    setSlideDirection(direction);
    setCurrentCard(index);
  }, [totalClaims]);

  const goNext = useCallback(() => {
    if (!isLastCard) goToCard(currentCard + 1, "right");
  }, [currentCard, isLastCard, goToCard]);

  const goPrev = useCallback(() => {
    if (!isFirstCard) goToCard(currentCard - 1, "left");
  }, [currentCard, isFirstCard, goToCard]);

  const isReviewed = (index: number): boolean => verdicts.has(index);

  const updateVerdict = (
    claimIndex: number,
    field: keyof ClaimVerdict,
    value: unknown
  ) => {
    setVerdicts((prev) => {
      const updated = new Map(prev);
      const current = updated.get(claimIndex) || {
        claim_index: claimIndex,
        verdict: "accept" as VerdictType,
      };
      updated.set(claimIndex, { ...current, [field]: value });
      return updated;
    });
  };

  const setVerdictType = useCallback((claimIndex: number, verdict: VerdictType) => {
    if (autoAdvanceTimer.current) clearTimeout(autoAdvanceTimer.current);

    setVerdicts((prev) => {
      const updated = new Map(prev);
      const current = updated.get(claimIndex) || {
        claim_index: claimIndex,
        verdict: "accept" as VerdictType,
      };
      updated.set(claimIndex, { ...current, verdict });
      return updated;
    });
    carouselRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });

    if (claimIndex < totalClaims - 1) {
      autoAdvanceTimer.current = setTimeout(() => goNext(), 300);
    }
  }, [totalClaims, goNext]);

  const handleSubmit = () => {
    const verdictList: ClaimVerdict[] = [];
    for (let i = 0; i < claims.length; i++) {
      const v = verdicts.get(i);
      if (v) {
        verdictList.push(v);
      } else {
        verdictList.push({
          claim_index: i,
          verdict: "accept",
        });
      }
    }
    onSubmit({
      type: "verdicts",
      verdicts: verdictList,
    });
  };

  const currentVerdict = verdicts.get(currentCard)?.verdict || "accept";
  const animationClass =
    slideDirection === "right" ? "animate-slide-in-right" : "animate-slide-in-left";

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white border border-gray-200/80 border-l-4 border-l-amber-400 rounded-xl shadow-sm p-5">
        <h2 className="flex items-center gap-2.5 text-sm font-semibold text-amber-600 uppercase tracking-wide">
          <i className="bi bi-clipboard-check text-base" />
          {t("verdicts.title")}
        </h2>
        <p className="text-gray-500 text-sm mt-1">
          {t("verdicts.description")}
        </p>
      </div>

      {/* Carousel */}
      {totalClaims > 0 && (
        <div ref={carouselRef} className="scroll-mt-4 bg-white border border-gray-200/80 border-l-4 border-l-amber-400 rounded-xl shadow-sm p-5">
          <div className="flex flex-col items-center">
            {/* Progress dots */}
            <div className="flex items-center gap-1.5 mb-4">
              {claims.map((_, i) => {
                const reviewed = isReviewed(i);
                const dotColor = reviewed ? "bg-amber-500" : "bg-gray-300";
                const ring = i === currentCard ? "ring-2 ring-amber-400 ring-offset-1" : "";
                return (
                  <button
                    key={i}
                    onClick={() => goToCard(i, i > currentCard ? "right" : "left")}
                    className={`w-2.5 h-2.5 rounded-full transition-all ${dotColor} ${ring}`}
                    aria-label={`Claim ${i + 1}`}
                  />
                );
              })}
            </div>

            {/* Card + navigation */}
            <div className="flex items-start gap-3 w-full">
              {/* Prev arrow */}
              <button
                onClick={goPrev}
                disabled={isFirstCard}
                className={`flex-shrink-0 w-9 h-9 mt-4 rounded-full flex items-center justify-center transition-colors ${
                  isFirstCard
                    ? "text-gray-300 cursor-not-allowed"
                    : "text-gray-500 hover:bg-amber-50 hover:text-amber-600"
                }`}
                aria-label="Previous claim"
              >
                <i className="bi bi-chevron-left text-lg" />
              </button>

              {/* Card content */}
              <div
                key={currentCard}
                className={`flex-1 space-y-4 ${animationClass}`}
              >
                {/* Counter */}
                <p className="text-xs text-gray-400 font-medium text-center">
                  {currentCard + 1} / {totalClaims}
                </p>

                {/* Claim card (compact) */}
                <ClaimCard claim={claims[currentCard]} index={currentCard} compact />

                {/* Verdict buttons */}
                <div className="grid grid-cols-4 gap-2">
                  {(["accept", "reject", "qualify", "merge"] as VerdictType[]).map((v) => (
                    <button
                      key={v}
                      onClick={() => setVerdictType(currentCard, v)}
                      className={`py-2 px-3 rounded-md font-medium text-xs transition-all ${
                        currentVerdict === v
                          ? VERDICT_STYLES[v].active
                          : VERDICT_STYLES[v].inactive
                      }`}
                    >
                      {t(VERDICT_KEYS[v])}
                    </button>
                  ))}
                </div>

                {/* Conditional inputs */}
                {currentVerdict === "reject" && (
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">
                      {t("verdicts.rejectionReason")}
                    </label>
                    <input
                      type="text"
                      value={verdicts.get(currentCard)?.rejection_reason || ""}
                      onChange={(e) =>
                        updateVerdict(currentCard, "rejection_reason", e.target.value)
                      }
                      className="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-red-400 focus:border-transparent placeholder-gray-400"
                    />
                  </div>
                )}

                {currentVerdict === "qualify" && (
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">
                      {t("verdicts.qualification")}
                    </label>
                    <input
                      type="text"
                      value={verdicts.get(currentCard)?.qualification || ""}
                      onChange={(e) =>
                        updateVerdict(currentCard, "qualification", e.target.value)
                      }
                      className="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent placeholder-gray-400"
                    />
                  </div>
                )}

                {currentVerdict === "merge" && (
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">
                      {t("verdicts.mergeWith")}
                    </label>
                    <select
                      value={verdicts.get(currentCard)?.merge_with_claim_id || ""}
                      onChange={(e) =>
                        updateVerdict(currentCard, "merge_with_claim_id", e.target.value)
                      }
                      className="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent"
                    >
                      <option value="">{t("verdicts.selectClaim")}</option>
                      {claims.map((c, origIdx) =>
                        origIdx !== currentCard ? (
                          <option key={origIdx} value={c.claim_id || `claim-${origIdx}`}>
                            #{origIdx + 1}: {c.claim_text.slice(0, 60)}...
                          </option>
                        ) : null
                      )}
                    </select>
                  </div>
                )}
              </div>

              {/* Next arrow */}
              <button
                onClick={goNext}
                disabled={isLastCard}
                className={`flex-shrink-0 w-9 h-9 mt-4 rounded-full flex items-center justify-center transition-colors ${
                  isLastCard
                    ? "text-gray-300 cursor-not-allowed"
                    : "text-gray-500 hover:bg-amber-50 hover:text-amber-600"
                }`}
                aria-label="Next claim"
              >
                <i className="bi bi-chevron-right text-lg" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Submit */}
      <button
        onClick={handleSubmit}
        className="w-full bg-amber-600 hover:bg-amber-500 text-white font-semibold text-sm py-3 px-6 rounded-lg transition-all"
      >
        {t("verdicts.submit")}
      </button>
    </div>
  );
}
