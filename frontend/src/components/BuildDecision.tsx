/* BuildDecision — Phase 5 build review with inline graph, gap carousel, and insight card.

Invariants:
    - Knowledge Graph rendered inline (not sidebar) when nodes exist
    - Gaps carousel follows centralized container pattern (max-w-lg) matching Phases 1-4
    - Gap selection is multi-select (checkboxes), no auto-advance
    - "Investigate Gaps" requires >= 1 gap selected
    - When gaps=0, free-text direction input replaces carousel
    - Deep Dive card shown only when !max_rounds_reached
    - "Finalize" button always visible, sends decision="resolve"

Design Decisions:
    - Gaps as carousel over list: visual consistency with Phases 1-4 (ADR: UX cohesion)
    - KnowledgeGraph embedded inline: removes sidebar split, all content in single column
    - Insight card inline over UserInsightForm page replacement: stays in carousel flow context
    - Multi-select gaps without auto-advance: user reviews all gaps before acting (ADR: multi-select UX)
*/

import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import type { BuildReviewData, UserInput } from "../types";
import KnowledgeGraph from "./KnowledgeGraph";
import ClaimMarkdown from "./ClaimMarkdown";

interface BuildDecisionProps {
  data: BuildReviewData;
  onSubmit: (input: UserInput) => void;
}

export default function BuildDecision({ data, onSubmit }: BuildDecisionProps) {
  const { t } = useTranslation();

  // Gap carousel state
  const [selectedGaps, setSelectedGaps] = useState<Set<number>>(new Set());
  const [currentGapCard, setCurrentGapCard] = useState(0);
  const [gapSlideDirection, setGapSlideDirection] = useState<"left" | "right">("right");

  // Free-text direction (when gaps=0)
  const [directionText, setDirectionText] = useState("");

  // Insight card state
  const [showInsight, setShowInsight] = useState(false);
  const [insightText, setInsightText] = useState("");
  const [insightUrls, setInsightUrls] = useState<string[]>([""]);

  // Deep dive state
  const [selectedClaimId, setSelectedClaimId] = useState("");

  // Validation
  const [error, setError] = useState("");

  const gaps = data.gaps;
  const totalGaps = gaps.length;
  const isFirstGap = currentGapCard <= 0;
  const isLastGap = currentGapCard >= totalGaps - 1;

  // -- Gap carousel navigation --

  const goToGapCard = useCallback((index: number, direction: "left" | "right") => {
    if (index < 0 || index >= totalGaps) return;
    setGapSlideDirection(direction);
    setCurrentGapCard(index);
  }, [totalGaps]);

  const goNextGap = useCallback(() => {
    if (!isLastGap) goToGapCard(currentGapCard + 1, "right");
  }, [currentGapCard, isLastGap, goToGapCard]);

  const goPrevGap = useCallback(() => {
    if (!isFirstGap) goToGapCard(currentGapCard - 1, "left");
  }, [currentGapCard, isFirstGap, goToGapCard]);

  // -- Handlers --

  const handleGapToggle = (index: number) => {
    setSelectedGaps((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index); else next.add(index);
      return next;
    });
  };

  const handleInvestigate = () => {
    setError("");
    if (selectedGaps.size === 0) {
      setError(t("build.selectClaim"));
      return;
    }
    onSubmit({
      type: "build_decision",
      decision: "continue",
      selected_gaps: [...selectedGaps],
    });
  };

  const handleDirection = () => {
    setError("");
    if (!directionText.trim()) return;
    onSubmit({
      type: "build_decision",
      decision: "continue",
      continue_direction: directionText.trim(),
    });
  };

  const handleDeepDive = () => {
    setError("");
    if (!selectedClaimId) {
      setError(t("build.selectClaim"));
      return;
    }
    onSubmit({
      type: "build_decision",
      decision: "deep_dive",
      deep_dive_claim_id: selectedClaimId,
    });
  };

  const handleInsight = () => {
    setError("");
    if (!insightText.trim()) {
      setError(t("insight.required"));
      return;
    }
    const filteredUrls = insightUrls.filter((u) => u.trim() !== "");
    onSubmit({
      type: "build_decision",
      decision: "add_insight",
      user_insight: insightText.trim(),
      user_evidence_urls: filteredUrls.length > 0 ? filteredUrls : undefined,
    });
  };

  const handleFinalize = () => {
    onSubmit({ type: "build_decision", decision: "resolve" });
  };

  const gapAnimationClass = gapSlideDirection === "right" ? "animate-slide-in-right" : "animate-slide-in-left";

  return (
    <div className="space-y-5">
      {/* Card 1: Knowledge Graph (inline) */}
      {data.graph.nodes.length > 0 && (
        <div className="bg-white border border-gray-200/80 rounded-xl shadow-md shadow-gray-200/40 overflow-hidden" style={{ height: "400px" }}>
          <KnowledgeGraph data={data.graph} />
        </div>
      )}

      {/* Card 2: Deep Dive (only when rounds remain) */}
      {!data.max_rounds_reached && (
        <div className="bg-white border border-gray-200/80 border-l-4 border-l-blue-400 rounded-xl shadow-sm p-5">
          <h3 className="flex items-center gap-2.5 text-sm font-semibold text-blue-600 uppercase tracking-wide mb-3">
            <i className="bi bi-search text-base" />
            {t("build.deepDiveTitle")}
          </h3>
          <div className="flex gap-2">
            <select
              value={selectedClaimId}
              onChange={(e) => setSelectedClaimId(e.target.value)}
              className="flex-1 bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">{t("build.selectClaim")}</option>
              {data.graph.nodes.map((node) => (
                <option key={node.id} value={node.id}>
                  {(node.data?.claim_text ?? "").slice(0, 60)}...
                </option>
              ))}
            </select>
            <button
              onClick={handleDeepDive}
              disabled={!selectedClaimId}
              className="bg-blue-500 hover:bg-blue-400 text-white py-2 px-4 rounded-md font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t("build.deepDiveAction")}
            </button>
          </div>
        </div>
      )}

      {/* Card 3: Knowledge Gaps (carousel or free-text) */}
      {!data.max_rounds_reached && (
        totalGaps > 0 ? (
          /* Carousel when gaps exist */
          <div className={`bg-white border border-gray-200/80 border-l-4 rounded-xl shadow-sm p-5 transition-all ${
            selectedGaps.size > 0 ? "border-l-green-500" : "border-l-gray-300"
          }`}>
            <h3 className={`flex items-center gap-2.5 text-sm font-semibold uppercase tracking-wide mb-4 ${
              selectedGaps.size > 0 ? "text-green-600" : "text-gray-400"
            }`}>
              <i className="bi bi-lightning text-base" />
              {t("build.gaps")}
              {selectedGaps.size > 0 && (
                <span className="ml-auto text-xs text-green-500 font-normal flex items-center gap-1">
                  <i className="bi bi-check-circle-fill text-[11px]" />
                </span>
              )}
            </h3>

            <div className="flex flex-col items-center">
              {/* Progress dots — green when selected */}
              <div className="flex items-center gap-1.5 mb-4">
                {gaps.map((_, i) => {
                  const dotColor = selectedGaps.has(i) ? "bg-green-500" : "bg-gray-300";
                  const ring = i === currentGapCard ? "ring-2 ring-green-400 ring-offset-1" : "";
                  return (
                    <button
                      key={i}
                      onClick={() => goToGapCard(i, i > currentGapCard ? "right" : "left")}
                      className={`w-2.5 h-2.5 rounded-full transition-all ${dotColor} ${ring}`}
                      aria-label={`Gap ${i + 1}`}
                    />
                  );
                })}
              </div>

              {/* Card + navigation — centralized max-w-lg */}
              <div className="flex items-center gap-3 w-full max-w-lg">
                <button
                  onClick={goPrevGap}
                  disabled={isFirstGap}
                  className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
                    isFirstGap ? "text-gray-300 cursor-not-allowed" : "text-gray-500 hover:bg-green-50 hover:text-green-600"
                  }`}
                  aria-label="Previous gap"
                >
                  <i className="bi bi-chevron-left text-lg" />
                </button>

                <div key={currentGapCard} className={`flex-1 p-5 rounded-lg text-center ${gapAnimationClass}`}>
                  <p className="text-xs text-gray-400 font-medium mb-2">{currentGapCard + 1} / {totalGaps}</p>
                  <div className="text-left max-w-md mx-auto mb-4">
                    <ClaimMarkdown className="text-sm text-gray-700 leading-relaxed">{gaps[currentGapCard]}</ClaimMarkdown>
                  </div>
                  <button
                    onClick={() => handleGapToggle(currentGapCard)}
                    className={`w-full py-2.5 px-4 rounded-md font-medium text-sm transition-all text-left ${
                      selectedGaps.has(currentGapCard)
                        ? "bg-green-600 text-white"
                        : "bg-white border border-gray-200 text-gray-600 hover:border-green-300 hover:text-green-600"
                    }`}
                  >
                    {selectedGaps.has(currentGapCard) ? (
                      <span className="flex items-center gap-2">
                        <i className="bi bi-check-circle-fill text-sm" />
                        {t("build.gapSelected")}
                      </span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <i className="bi bi-circle text-sm" />
                        {t("build.gapSelected")}
                      </span>
                    )}
                  </button>
                </div>

                <button
                  onClick={goNextGap}
                  disabled={isLastGap}
                  className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
                    isLastGap ? "text-gray-300 cursor-not-allowed" : "text-gray-500 hover:bg-green-50 hover:text-green-600"
                  }`}
                  aria-label="Next gap"
                >
                  <i className="bi bi-chevron-right text-lg" />
                </button>
              </div>
            </div>

            {/* Investigate button */}
            <button
              onClick={handleInvestigate}
              disabled={selectedGaps.size === 0}
              className="w-full mt-4 bg-green-600 hover:bg-green-500 text-white font-semibold text-sm py-3 px-6 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t("build.investigateGaps", { count: selectedGaps.size })}
            </button>
          </div>
        ) : (
          /* Free-text direction when no gaps */
          <div className="bg-white border border-gray-200/80 border-l-4 border-l-gray-300 rounded-xl shadow-sm p-5">
            <h3 className="flex items-center gap-2.5 text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
              <i className="bi bi-lightning text-base" />
              {t("build.gaps")}
            </h3>
            <p className="text-sm text-gray-500 mb-3">{t("build.noGaps")}</p>
            <textarea
              value={directionText}
              onChange={(e) => setDirectionText(e.target.value)}
              rows={3}
              className="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none placeholder-gray-400 mb-3"
            />
            <button
              onClick={handleDirection}
              disabled={!directionText.trim()}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm py-3 px-6 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t("build.startRound")}
            </button>
          </div>
        )
      )}

      {/* Card 4: Insight (collapsible) */}
      <div className="bg-white border border-gray-200/80 border-l-4 border-l-indigo-400 rounded-xl shadow-sm">
        <button
          onClick={() => setShowInsight(!showInsight)}
          className="w-full flex items-center gap-2.5 px-5 py-4 text-sm font-semibold text-indigo-600 uppercase tracking-wide hover:bg-indigo-50/30 transition-colors"
        >
          <i className="bi bi-lightbulb text-base" />
          {t("build.insightCard")}
          <span className={`ml-auto transition-transform ${showInsight ? "rotate-90" : ""}`}>&#9654;</span>
        </button>
        {showInsight && (
          <div className="px-5 pb-5 space-y-3 animate-fade-in">
            <div>
              <label className="block text-xs text-gray-500 mb-2">{t("insight.label")}</label>
              <textarea
                value={insightText}
                onChange={(e) => setInsightText(e.target.value)}
                placeholder={t("insight.placeholder")}
                rows={4}
                className="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none placeholder-gray-400"
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs text-gray-500">{t("insight.urlLabel")}</label>
                <button
                  onClick={() => setInsightUrls([...insightUrls, ""])}
                  className="text-indigo-600 hover:text-indigo-500 text-xs font-medium"
                >
                  {t("insight.addUrl")}
                </button>
              </div>
              <div className="space-y-2">
                {insightUrls.map((url, i) => (
                  <div key={i} className="flex gap-2">
                    <input
                      type="text"
                      value={url}
                      onChange={(e) => {
                        const updated = [...insightUrls];
                        updated[i] = e.target.value;
                        setInsightUrls(updated);
                      }}
                      placeholder={t("insight.urlPlaceholder")}
                      className="flex-1 bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent placeholder-gray-400"
                    />
                    {insightUrls.length > 1 && (
                      <button
                        onClick={() => setInsightUrls(insightUrls.filter((_, j) => j !== i))}
                        className="bg-white border border-gray-200 hover:bg-indigo-50 hover:border-indigo-200 text-gray-500 hover:text-indigo-600 px-3 py-2 rounded-md text-xs font-medium transition-colors"
                      >
                        {t("insight.remove")}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
            <button
              onClick={handleInsight}
              disabled={!insightText.trim()}
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm py-3 px-6 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t("insight.submit")}
            </button>
          </div>
        )}
      </div>

      {/* Card 5: Finalize */}
      <button
        onClick={handleFinalize}
        className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm py-3 px-6 rounded-lg transition-all"
      >
        {t("build.finalize")}
      </button>

      {/* Error */}
      {error && (
        <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-4 py-2">{error}</p>
      )}

      {/* Max rounds warning */}
      {data.max_rounds_reached && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-blue-700 text-sm">{t("build.maxRounds")}</p>
        </div>
      )}
    </div>
  );
}
