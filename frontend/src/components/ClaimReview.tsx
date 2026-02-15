/* ClaimReview — Phase 3 review UI with carousel + resonance assessment.

Invariants:
    - At least 1 claim must resonate (option > 0) or user adds a custom claim before submit
    - Carousel allows free navigation through claims
    - Option selection auto-advances to next card after brief visual feedback
    - Collapsible reasoning/falsifiability details per claim

Design Decisions:
    - Mirrors DecomposeReview carousel pattern (ADR: consistent UX across phases)
    - Option 0 = gray "no resonance", options 1+ = green resonance (same as reframings)
    - Fallback to ClaimCard list when no resonance data (backward compat with old sessions)
    - Auto-collapse 400ms after all claims reviewed
*/

import { useState, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import type { Claim, ClaimFeedback, UserInput } from "../types";
import ClaimCard from "./ClaimCard";

interface ClaimReviewProps {
  claims: Claim[];
  onSubmit: (input: UserInput) => void;
}

export default function ClaimReview({ claims, onSubmit }: ClaimReviewProps) {
  const { t } = useTranslation();

  // -- Carousel state --
  const [responses, setResponses] = useState<Map<number, number>>(new Map());
  const [currentCard, setCurrentCard] = useState(0);
  const [slideDirection, setSlideDirection] = useState<"left" | "right">("right");
  const autoAdvanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [done, setDone] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [expandedDetails, setExpandedDetails] = useState<Set<number>>(new Set());

  // -- Manual input --
  const [newClaim, setNewClaim] = useState("");

  // -- Legacy fallback state --
  const [feedback, setFeedback] = useState<Map<number, ClaimFeedback>>(new Map());

  // -- Derived --
  const totalClaims = claims.length;
  const hasResonanceData = claims.some(c => c.resonance_options && c.resonance_options.length > 0);
  const allReviewed = totalClaims > 0 && responses.size >= totalClaims;
  const hasResonance = Array.from(responses.values()).some(opt => opt > 0);
  const canSubmit = hasResonance || newClaim.trim().length > 0;
  const isLastCard = currentCard >= totalClaims - 1;
  const isFirstCard = currentCard <= 0;

  // -- Carousel navigation --
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

  const selectOption = useCallback((claimIndex: number, optionIndex: number) => {
    if (autoAdvanceTimer.current) clearTimeout(autoAdvanceTimer.current);

    setResponses((prev) => {
      const next = new Map(prev);
      if (next.get(claimIndex) === optionIndex) {
        next.delete(claimIndex);
      } else {
        next.set(claimIndex, optionIndex);
      }

      if (next.size >= totalClaims) {
        autoAdvanceTimer.current = setTimeout(() => {
          setDone(true);
          setCollapsed(true);
        }, 400);
      } else if (claimIndex < totalClaims - 1) {
        autoAdvanceTimer.current = setTimeout(() => goNext(), 300);
      }

      return next;
    });
  }, [totalClaims, goNext]);

  // -- Details toggle --
  const toggleDetails = (index: number) => {
    setExpandedDetails((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index); else next.add(index);
      return next;
    });
  };

  // -- Legacy feedback --
  const updateFeedback = (
    claimIndex: number,
    field: keyof ClaimFeedback,
    value: unknown,
  ) => {
    setFeedback((prev) => {
      const updated = new Map(prev);
      const current = updated.get(claimIndex) || {
        claim_index: claimIndex,
        evidence_valid: false,
      };
      updated.set(claimIndex, { ...current, [field]: value });
      return updated;
    });
  };

  // -- Submit --
  const handleSubmit = () => {
    if (hasResonanceData) {
      const input: UserInput = {
        type: "claims_review",
        claim_responses: Array.from(responses.entries()).map(
          ([idx, opt]) => ({ claim_index: idx, selected_option: opt }),
        ),
        added_claims: newClaim.trim() ? [newClaim.trim()] : undefined,
      };
      onSubmit(input);
    } else {
      const claim_feedback: ClaimFeedback[] = [];
      for (let i = 0; i < claims.length; i++) {
        const fb = feedback.get(i);
        claim_feedback.push(fb || { claim_index: i, evidence_valid: false });
      }
      onSubmit({
        type: "claims_review",
        claim_feedback,
        added_claims: newClaim.trim() ? [newClaim.trim()] : undefined,
      });
    }
  };

  const isReviewed = (index: number): boolean => responses.has(index);
  const claim = claims[currentCard];
  const animationClass =
    slideDirection === "right" ? "animate-slide-in-right" : "animate-slide-in-left";

  // ---- Resonance carousel layout ----
  if (hasResonanceData) {
    return (
      <div className="space-y-4">
        {collapsed ? (
          <div
            onClick={() => { setCollapsed(false); setDone(false); }}
            className="bg-white border border-gray-200/80 border-l-4 border-l-green-500 rounded-xl shadow-sm p-4 cursor-pointer hover:bg-green-50/30 transition-colors animate-fade-in"
          >
            <div className="flex items-center gap-2.5">
              <i className="bi bi-patch-check-fill text-green-500 text-base" />
              <span className="text-sm font-semibold text-green-600 uppercase tracking-wide flex-1">
                {t("claims.title")} ({totalClaims}/{totalClaims})
              </span>
              <span className="text-xs text-gray-400 flex items-center gap-1">
                <i className="bi bi-pencil text-[10px]" />
                {t("claims.edit")}
              </span>
            </div>
          </div>
        ) : (
          <div className={`bg-white border border-gray-200/80 border-l-4 rounded-xl shadow-sm p-5 transition-all ${
            hasResonance ? "border-l-green-500" : "border-l-gray-300"
          } ${done ? "animate-fade-in" : ""}`}>
            <h3 className={`flex items-center gap-2.5 text-sm font-semibold uppercase tracking-wide mb-4 ${
              hasResonance ? "text-green-600" : "text-gray-400"
            }`}>
              <i className="bi bi-lightbulb text-base" />
              {t("claims.title")}
              {allReviewed && (
                <span className="ml-auto text-xs text-green-500 font-normal flex items-center gap-1">
                  <i className="bi bi-check-circle-fill text-[11px]" />
                </span>
              )}
            </h3>

            {totalClaims > 0 && claim && (
              <div className="flex flex-col items-center">
                {/* Progress dots */}
                <div className="flex items-center gap-1.5 mb-4">
                  {claims.map((_, i) => {
                    const reviewed = isReviewed(i);
                    const responded = responses.get(i);
                    const dotColor = reviewed
                      ? (responded !== undefined && responded > 0 ? "bg-green-500" : "bg-gray-400")
                      : "bg-gray-300";
                    const ring = i === currentCard ? "ring-2 ring-green-400 ring-offset-1" : "";
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
                <div className="flex items-center gap-3 w-full max-w-lg">
                  <button
                    onClick={goPrev}
                    disabled={isFirstCard}
                    className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
                      isFirstCard
                        ? "text-gray-300 cursor-not-allowed"
                        : "text-gray-500 hover:bg-green-50 hover:text-green-600"
                    }`}
                    aria-label="Previous claim"
                  >
                    <i className="bi bi-chevron-left text-lg" />
                  </button>

                  <div
                    key={currentCard}
                    className={`flex-1 p-5 rounded-lg text-center ${animationClass}`}
                  >
                    <p className="text-xs text-gray-400 font-medium mb-2">
                      {currentCard + 1} / {totalClaims}
                    </p>
                    <div className="text-left max-w-md mx-auto mb-2">
                      <p className="text-gray-700 text-sm leading-relaxed">
                        {claim.reasoning || claim.claim_text}
                      </p>
                    </div>

                    {/* Collapsible details */}
                    <button
                      onClick={() => toggleDetails(currentCard)}
                      className="text-xs text-gray-400 hover:text-gray-600 transition-colors mb-3 inline-flex items-center gap-1"
                    >
                      <i className={`bi ${expandedDetails.has(currentCard) ? "bi-chevron-up" : "bi-chevron-down"} text-[10px]`} />
                      {expandedDetails.has(currentCard) ? t("claims.hideDetails") : t("claims.showDetails")}
                    </button>

                    {expandedDetails.has(currentCard) && (
                      <div className="text-left max-w-md mx-auto mb-3 space-y-2 animate-fade-in">
                        {claim.falsifiability_condition && (
                          <div>
                            <p className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold">{t("common.falsifiability")}</p>
                            <p className="text-xs text-gray-500 leading-relaxed">{claim.falsifiability_condition}</p>
                          </div>
                        )}
                        {claim.evidence && claim.evidence.length > 0 && (
                          <div>
                            <p className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold">
                              {t("evidence.title")} ({claim.evidence.length})
                            </p>
                            {claim.evidence.map((ev, ei) => (
                              <p key={ei} className="text-xs text-gray-500 truncate">
                                <a href={ev.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
                                  {ev.title || ev.url}
                                </a>
                              </p>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Resonance prompt */}
                    {claim.resonance_prompt && (
                      <div className="text-left max-w-md mx-auto mb-4">
                        <p className="text-gray-500 text-sm italic font-medium">
                          {claim.resonance_prompt}
                        </p>
                      </div>
                    )}

                    {/* Resonance option buttons */}
                    {claim.resonance_options && claim.resonance_options.length > 0 && (
                      <div className="flex flex-col gap-2">
                        {claim.resonance_options.map((option, optIdx) => {
                          const selected = responses.get(currentCard) === optIdx;
                          return (
                            <button
                              key={optIdx}
                              onClick={() => selectOption(currentCard, optIdx)}
                              className={`w-full px-4 py-2 rounded-md text-xs font-medium transition-all text-left ${
                                selected
                                  ? optIdx === 0
                                    ? "bg-gray-400 text-white shadow-sm shadow-gray-200"
                                    : "bg-green-500 text-white shadow-sm shadow-green-200"
                                  : optIdx === 0
                                    ? "bg-white border border-gray-300 text-gray-500 hover:border-gray-400"
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

                  <button
                    onClick={goNext}
                    disabled={isLastCard}
                    className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
                      isLastCard
                        ? "text-gray-300 cursor-not-allowed"
                        : "text-gray-500 hover:bg-green-50 hover:text-green-600"
                    }`}
                    aria-label="Next claim"
                  >
                    <i className="bi bi-chevron-right text-lg" />
                  </button>
                </div>
              </div>
            )}

            <input
              type="text"
              value={newClaim}
              onChange={(e) => setNewClaim(e.target.value)}
              placeholder={t("claims.addClaim")}
              className="mt-4 w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-gray-700 text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-400 focus:border-transparent"
            />
          </div>
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="w-full py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-200 disabled:text-gray-400 disabled:shadow-none disabled:cursor-not-allowed text-white font-semibold text-sm rounded-lg shadow-md shadow-green-200/50 hover:shadow-lg hover:shadow-green-300/50 transition-all inline-flex items-center justify-center gap-2 animate-fade-in"
        >
          {t("claims.submit")}
        </button>
      </div>
    );
  }

  // ---- Legacy fallback (no resonance data) ----
  return (
    <div className="space-y-5">
      {claims.map((c, i) => (
        <div key={i} className="space-y-3">
          <ClaimCard claim={c} index={i} />
          <div className="bg-white border border-gray-200/80 rounded-xl shadow-md shadow-gray-200/40 p-5 space-y-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={feedback.get(i)?.evidence_valid || false}
                onChange={(e) => updateFeedback(i, "evidence_valid", e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-gray-900 text-sm font-medium">
                {t("claims.evidenceValid")}
              </span>
            </label>
          </div>
        </div>
      ))}

      <input
        type="text"
        value={newClaim}
        onChange={(e) => setNewClaim(e.target.value)}
        placeholder={t("claims.addClaim")}
        className="w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-gray-700 text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-400 focus:border-transparent"
      />

      <button
        onClick={handleSubmit}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm py-3 px-6 rounded-lg shadow-md shadow-blue-200/50 hover:shadow-lg hover:shadow-blue-300/50 transition-all"
      >
        {t("claims.submit")}
      </button>
    </div>
  );
}
