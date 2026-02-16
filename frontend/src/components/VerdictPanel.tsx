/* VerdictPanel — Phase 4 verdict UI with carousel navigation and auto-collapse.

Invariants:
    - All verdict buttons start unselected — user must explicitly choose
    - Carousel follows centralized container pattern (max-w-lg) matching Phases 1-3
    - Accept auto-advances to next card (300ms); reject/qualify/merge stay for input
    - Auto-collapses into summary bar after all accept-only verdicts reviewed (400ms)
    - Progress dots reflect verdict-semantic colors (emerald/red/amber/violet)

Design Decisions:
    - Inline claim display over ClaimCard embed: avoids card-within-card visual noise (ADR: Phase 1-3 consistency)
    - Stacked buttons over grid-cols-4: better readability at mobile sizes, matches resonance option pattern
    - Verdict-colored dots over uniform amber: provides at-a-glance verdict distribution feedback
    - Collapsible details toggle: shows scores/evidence on demand without cluttering the decision flow
*/

import { useState, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import type { Claim, ClaimVerdict, UserInput, VerdictType } from "../types";
import ClaimMarkdown from "./ClaimMarkdown";

interface VerdictPanelProps {
  claims: Claim[];
  onSubmit: (input: UserInput) => void;
}

/* ADR: merged dot/key/style into single record to stay under 400-line limit */
const VERDICT_META: Record<VerdictType, { key: string; dot: string; active: string; inactive: string }> = {
  accept:  { key: "verdicts.accept",  dot: "bg-emerald-500", active: "bg-emerald-600 text-white", inactive: "bg-white border border-gray-200 text-gray-600 hover:border-emerald-300 hover:text-emerald-600" },
  reject:  { key: "verdicts.reject",  dot: "bg-red-500",     active: "bg-red-500 text-white",     inactive: "bg-white border border-gray-200 text-gray-600 hover:border-red-300 hover:text-red-500" },
  qualify: { key: "verdicts.qualify",  dot: "bg-amber-500",   active: "bg-amber-500 text-white",   inactive: "bg-white border border-gray-200 text-gray-600 hover:border-amber-300 hover:text-amber-600" },
  merge:   { key: "verdicts.merge",   dot: "bg-violet-500",  active: "bg-violet-500 text-white",  inactive: "bg-white border border-gray-200 text-gray-600 hover:border-violet-300 hover:text-violet-600" },
};

const SCORE_COLORS: Record<string, string> = {
  novelty: "bg-violet-500", groundedness: "bg-amber-500", falsifiability: "bg-cyan-500", significance: "bg-rose-500",
};
const SCORE_KEY: Record<string, string> = {
  novelty: "score.novelty", groundedness: "score.groundedness", falsifiability: "score.falsifiability", significance: "score.significance",
};
const CLAIM_TYPE_COLOR: Record<string, string> = {
  thesis: "bg-blue-50 text-blue-600 border border-blue-200", antithesis: "bg-orange-50 text-orange-600 border border-orange-200",
  synthesis: "bg-indigo-50 text-indigo-600 border border-indigo-200", user_contributed: "bg-green-50 text-green-600 border border-green-200",
  merged: "bg-purple-50 text-purple-600 border border-purple-200",
};
const CLAIM_TYPE_KEY: Record<string, string> = {
  thesis: "claims.type.thesis", antithesis: "claims.type.antithesis", synthesis: "claims.type.synthesis",
  user_contributed: "claims.type.user_contributed", merged: "claims.type.merged",
};
const CONFIDENCE_BADGE: Record<string, string> = {
  speculative: "bg-gray-50 text-gray-500 border border-gray-200", emerging: "bg-amber-50 text-amber-600 border border-amber-200",
  grounded: "bg-green-50 text-green-600 border border-green-200",
};
const CONFIDENCE_KEY: Record<string, string> = {
  speculative: "claims.confidence.speculative", emerging: "claims.confidence.emerging", grounded: "claims.confidence.grounded",
};

const VERDICT_LIST: VerdictType[] = ["accept", "reject", "qualify", "merge"];

/* ADR: verdicts needing extra input must NOT auto-advance — user needs time to fill the field */
const NEEDS_INPUT = new Set<VerdictType>(["reject", "qualify", "merge"]);

const isVerdictComplete = (v: ClaimVerdict): boolean => {
  if (v.verdict === "reject" && !v.rejection_reason) return false;
  if (v.verdict === "qualify" && !v.qualification) return false;
  if (v.verdict === "merge" && !v.merge_with_claim_id) return false;
  return true;
};

export default function VerdictPanel({ claims, onSubmit }: VerdictPanelProps) {
  const { t } = useTranslation();
  const [verdicts, setVerdicts] = useState<Map<number, ClaimVerdict>>(new Map());
  const [currentCard, setCurrentCard] = useState(0);
  const [slideDirection, setSlideDirection] = useState<"left" | "right">("right");
  const autoAdvanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const carouselRef = useRef<HTMLDivElement>(null);
  const [done, setDone] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [expandedDetails, setExpandedDetails] = useState<Set<number>>(new Set());

  const totalClaims = claims.length;
  const isLastCard = currentCard >= totalClaims - 1;
  const isFirstCard = currentCard <= 0;
  const allReviewed = totalClaims > 0 && verdicts.size >= totalClaims;

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

  const updateVerdict = (claimIndex: number, field: keyof ClaimVerdict, value: unknown) => {
    setVerdicts((prev) => {
      const updated = new Map(prev);
      const current = updated.get(claimIndex) || { claim_index: claimIndex, verdict: "accept" as VerdictType };
      updated.set(claimIndex, { ...current, [field]: value });
      return updated;
    });
  };

  const setVerdictType = useCallback((claimIndex: number, verdict: VerdictType) => {
    if (autoAdvanceTimer.current) clearTimeout(autoAdvanceTimer.current);
    setVerdicts((prev) => {
      const updated = new Map(prev);
      const current = updated.get(claimIndex) || { claim_index: claimIndex, verdict: "accept" as VerdictType };
      updated.set(claimIndex, { ...current, verdict });
      /* Only auto-advance for verdicts that don't need additional input */
      if (!NEEDS_INPUT.has(verdict)) {
        if (updated.size >= totalClaims) {
          autoAdvanceTimer.current = setTimeout(() => { setDone(true); setCollapsed(true); }, 400);
        } else if (claimIndex < totalClaims - 1) {
          autoAdvanceTimer.current = setTimeout(() => goNext(), 300);
        }
      }
      return updated;
    });
    /* ADR: verdicts needing input don't scroll — scroll deferred until input is confirmed */
    if (!NEEDS_INPUT.has(verdict)) {
      carouselRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [totalClaims, goNext]);

  const toggleDetails = (index: number) => {
    setExpandedDetails((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index); else next.add(index);
      return next;
    });
  };

  /* Confirm qualify/merge input → scroll to top, auto-advance or collapse */
  const confirmAndAdvance = useCallback(() => {
    if (autoAdvanceTimer.current) clearTimeout(autoAdvanceTimer.current);
    carouselRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    if (isLastCard) {
      autoAdvanceTimer.current = setTimeout(() => { setDone(true); setCollapsed(true); }, 400);
    } else {
      autoAdvanceTimer.current = setTimeout(() => goNext(), 300);
    }
  }, [isLastCard, goNext]);

  const handleSubmit = () => {
    const verdictList: ClaimVerdict[] = claims.map((_, i) =>
      verdicts.get(i) || { claim_index: i, verdict: "accept" },
    );
    const incomplete = verdictList.findIndex((v) => !isVerdictComplete(v));
    if (incomplete !== -1) {
      setCollapsed(false);
      setDone(false);
      goToCard(incomplete, incomplete > currentCard ? "right" : "left");
      return;
    }
    onSubmit({ type: "verdicts", verdicts: verdictList });
  };

  const currentVerdict = verdicts.get(currentCard)?.verdict;
  const claim = claims[currentCard];
  const animationClass = slideDirection === "right" ? "animate-slide-in-right" : "animate-slide-in-left";
  const allComplete = totalClaims > 0 && claims.every((_, i) => {
    const v = verdicts.get(i);
    return v ? isVerdictComplete(v) : true; /* unset defaults to accept — always complete */
  });

  return (
    <div className="space-y-4">
      {collapsed ? (
        <div
          onClick={() => { setCollapsed(false); setDone(false); }}
          className="bg-white border border-gray-200/80 border-l-4 border-l-amber-500 rounded-xl shadow-sm p-4 cursor-pointer hover:bg-amber-50/30 transition-colors animate-fade-in"
        >
          <div className="flex items-center gap-2.5">
            <i className="bi bi-patch-check-fill text-amber-500 text-base" />
            <span className="text-sm font-semibold text-amber-600 uppercase tracking-wide flex-1">
              {t("verdicts.title")} ({totalClaims}/{totalClaims})
            </span>
            <span className="text-xs text-gray-400 flex items-center gap-1">
              <i className="bi bi-pencil text-[10px]" /> {t("claims.edit")}
            </span>
          </div>
        </div>
      ) : totalClaims > 0 && claim && (
        <div ref={carouselRef} className={`scroll-mt-4 bg-white border border-gray-200/80 border-l-4 rounded-xl shadow-sm p-5 transition-all ${
          allReviewed ? "border-l-amber-500" : "border-l-gray-300"
        } ${done ? "animate-fade-in" : ""}`}>
          <h3 className={`flex items-center gap-2.5 text-sm font-semibold uppercase tracking-wide mb-4 ${
            allReviewed ? "text-amber-600" : "text-gray-400"
          }`}>
            <i className="bi bi-clipboard-check text-base" />
            {t("verdicts.title")}
            {allReviewed && (
              <span className="ml-auto text-xs text-amber-500 font-normal flex items-center gap-1">
                <i className="bi bi-check-circle-fill text-[11px]" />
              </span>
            )}
          </h3>

          <div className="flex flex-col items-center">
            {/* Progress dots — verdict-semantic colors */}
            <div className="flex items-center gap-1.5 mb-4">
              {claims.map((_, i) => {
                const v = verdicts.get(i)?.verdict;
                const dotColor = v ? VERDICT_META[v].dot : "bg-gray-300";
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

            {/* Card + navigation — centralized max-w-lg */}
            <div className="flex items-center gap-3 w-full max-w-lg">
              <button
                onClick={goPrev}
                disabled={isFirstCard}
                className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
                  isFirstCard ? "text-gray-300 cursor-not-allowed" : "text-gray-500 hover:bg-amber-50 hover:text-amber-600"
                }`}
                aria-label="Previous claim"
              >
                <i className="bi bi-chevron-left text-lg" />
              </button>

              <div key={currentCard} className={`flex-1 p-5 rounded-lg text-center ${animationClass}`}>
                <p className="text-xs text-gray-400 font-medium mb-2">{currentCard + 1} / {totalClaims}</p>

                {/* Badges — claim type + confidence */}
                <div className="flex items-center justify-center gap-2 mb-3">
                  {claim.claim_type && CLAIM_TYPE_KEY[claim.claim_type] && (
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${CLAIM_TYPE_COLOR[claim.claim_type] || "bg-gray-50 text-gray-600 border border-gray-200"}`}>
                      {t(CLAIM_TYPE_KEY[claim.claim_type])}
                    </span>
                  )}
                  {claim.confidence && CONFIDENCE_KEY[claim.confidence] && (
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${CONFIDENCE_BADGE[claim.confidence] || "bg-gray-50 text-gray-600 border border-gray-200"}`}>
                      {t(CONFIDENCE_KEY[claim.confidence])}
                    </span>
                  )}
                </div>

                {/* Claim text — always visible, left-aligned */}
                <div className="text-left max-w-md mx-auto mb-3">
                  <ClaimMarkdown className="text-sm text-gray-700 leading-relaxed">{claim.claim_text}</ClaimMarkdown>
                </div>

                {/* Toggle details */}
                <button
                  onClick={() => toggleDetails(currentCard)}
                  className="text-xs text-gray-400 hover:text-gray-600 transition-colors mb-4 inline-flex items-center gap-1"
                >
                  <i className={`bi ${expandedDetails.has(currentCard) ? "bi-chevron-up" : "bi-chevron-down"} text-[10px]`} />
                  {expandedDetails.has(currentCard) ? t("claims.hideDetails") : t("claims.showDetails")}
                </button>

                {/* Expandable details: scores, reasoning, falsifiability, evidence */}
                {expandedDetails.has(currentCard) && (
                  <div className="text-left max-w-md mx-auto mb-4 space-y-3 animate-fade-in">
                    {claim.scores && (
                      <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                        {Object.entries(claim.scores).map(([key, value]) => value !== null ? (
                          <div key={key}>
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs text-gray-500 capitalize">{t(SCORE_KEY[key] || key)}</span>
                              <span className="text-xs text-gray-700 font-semibold tabular-nums">{Math.round(value * 100)}%</span>
                            </div>
                            <div className="w-full bg-gray-100 rounded-full h-1.5">
                              <div className={`${SCORE_COLORS[key] || "bg-blue-500"} h-1.5 rounded-full transition-all duration-300`} style={{ width: `${value * 100}%` }} />
                            </div>
                          </div>
                        ) : null)}
                      </div>
                    )}
                    {claim.reasoning && (
                      <div>
                        <p className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold">{t("common.reasoning")}</p>
                        <ClaimMarkdown>{claim.reasoning}</ClaimMarkdown>
                      </div>
                    )}
                    {claim.falsifiability_condition && (
                      <div>
                        <p className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold">{t("common.falsifiability")}</p>
                        <ClaimMarkdown>{claim.falsifiability_condition}</ClaimMarkdown>
                      </div>
                    )}
                    {claim.score_reasoning && (
                      <div>
                        <p className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold">{t("common.scoreReasoning")}</p>
                        <ClaimMarkdown>{claim.score_reasoning}</ClaimMarkdown>
                      </div>
                    )}
                    {claim.evidence && claim.evidence.length > 0 && (
                      <div>
                        <p className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold">{t("evidence.title")} ({claim.evidence.length})</p>
                        {claim.evidence.map((ev, ei) => (
                          <p key={ei} className="text-xs text-gray-500 truncate">
                            <a href={ev.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">{ev.title || ev.url}</a>
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Verdict buttons — stacked full-width */}
                <div className="flex flex-col gap-2">
                  {VERDICT_LIST.map((v) => {
                    const meta = VERDICT_META[v];
                    return (
                      <button
                        key={v}
                        onClick={() => setVerdictType(currentCard, v)}
                        className={`w-full py-2.5 px-4 rounded-md font-medium text-sm transition-all text-left ${currentVerdict === v ? meta.active : meta.inactive}`}
                      >
                        {t(meta.key)}
                      </button>
                    );
                  })}
                </div>

                {/* Conditional inputs with fade-in */}
                {currentVerdict === "reject" && (
                  <div className="animate-fade-in text-left max-w-md mx-auto mt-3">
                    <label className="block text-xs text-gray-500 mb-1">{t("verdicts.rejectionReason")}</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        autoFocus
                        placeholder={t("verdicts.rejectionReason")}
                        value={verdicts.get(currentCard)?.rejection_reason || ""}
                        onChange={(e) => updateVerdict(currentCard, "rejection_reason", e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Enter" && verdicts.get(currentCard)?.rejection_reason) confirmAndAdvance(); }}
                        className="flex-1 bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-red-400 focus:border-transparent placeholder-gray-400"
                      />
                      <button
                        onClick={() => { if (verdicts.get(currentCard)?.rejection_reason) confirmAndAdvance(); }}
                        disabled={!verdicts.get(currentCard)?.rejection_reason}
                        className={`flex-shrink-0 w-9 h-9 rounded-md flex items-center justify-center transition-colors ${
                          verdicts.get(currentCard)?.rejection_reason
                            ? "bg-red-500 text-white hover:bg-red-600"
                            : "bg-gray-100 text-gray-300 cursor-not-allowed"
                        }`}
                        aria-label="Confirm rejection"
                      >
                        <i className="bi bi-plus-lg text-sm" />
                      </button>
                    </div>
                  </div>
                )}
                {currentVerdict === "qualify" && (
                  <div className="animate-fade-in text-left max-w-md mx-auto mt-3">
                    <label className="block text-xs text-gray-500 mb-1">{t("verdicts.qualification")}</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        autoFocus
                        placeholder={t("verdicts.qualification")}
                        value={verdicts.get(currentCard)?.qualification || ""}
                        onChange={(e) => updateVerdict(currentCard, "qualification", e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Enter" && verdicts.get(currentCard)?.qualification) confirmAndAdvance(); }}
                        className="flex-1 bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent placeholder-gray-400"
                      />
                      <button
                        onClick={() => { if (verdicts.get(currentCard)?.qualification) confirmAndAdvance(); }}
                        disabled={!verdicts.get(currentCard)?.qualification}
                        className={`flex-shrink-0 w-9 h-9 rounded-md flex items-center justify-center transition-colors ${
                          verdicts.get(currentCard)?.qualification
                            ? "bg-amber-500 text-white hover:bg-amber-600"
                            : "bg-gray-100 text-gray-300 cursor-not-allowed"
                        }`}
                        aria-label="Confirm qualification"
                      >
                        <i className="bi bi-plus-lg text-sm" />
                      </button>
                    </div>
                  </div>
                )}
                {currentVerdict === "merge" && (
                  <div className="animate-fade-in text-left max-w-md mx-auto mt-3">
                    <label className="block text-xs text-gray-500 mb-1">{t("verdicts.mergeWith")}</label>
                    <select
                      autoFocus
                      value={verdicts.get(currentCard)?.merge_with_claim_id || ""}
                      onChange={(e) => {
                        updateVerdict(currentCard, "merge_with_claim_id", e.target.value);
                        if (e.target.value) setTimeout(() => confirmAndAdvance(), 300);
                      }}
                      className="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent"
                    >
                      <option value="">{t("verdicts.selectClaim")}</option>
                      {claims.map((c, origIdx) => origIdx !== currentCard ? (
                        <option key={origIdx} value={c.claim_id || `claim-${origIdx}`}>
                          #{origIdx + 1}: {c.claim_text.slice(0, 60)}...
                        </option>
                      ) : null)}
                    </select>
                  </div>
                )}
              </div>

              <button
                onClick={goNext}
                disabled={isLastCard}
                className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
                  isLastCard ? "text-gray-300 cursor-not-allowed" : "text-gray-500 hover:bg-amber-50 hover:text-amber-600"
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
        className={`w-full font-semibold text-sm py-3 px-6 rounded-lg transition-all ${
          allComplete
            ? "bg-amber-600 hover:bg-amber-500 text-white"
            : "bg-gray-200 text-gray-400 cursor-not-allowed"
        }`}
      >
        {t("verdicts.submit")}
      </button>
    </div>
  );
}
