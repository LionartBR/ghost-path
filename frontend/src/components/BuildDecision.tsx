/* BuildDecision — Phase 5 build review layout orchestrator.

Invariants:
    - Knowledge Graph rendered inline (not sidebar) when nodes exist
    - Negative Knowledge card rendered when rejected claims exist, collapsed by default
    - Deep Dive card shown only when !max_rounds_reached
    - Gap triage delegated to GapCarousel component (extracted for ExMA line limits)
    - When gaps=0, free-text direction input replaces carousel
    - Continue and Finalize buttons both carry selected gaps automatically
    - Card order: Graph → Negative Knowledge → Deep Dive → Gaps → Insight → Continue/Finalize

Design Decisions:
    - GapCarousel extracted: keeps both files under 400-line ExMA limit (ADR: file size)
    - GapCarousel is triage-only (no CTA): parent owns submit via Continue/Finalize
      (ADR: users clicked Finalize ignoring carousel CTA, skipping gap investigation)
    - Selected gaps auto-included in both Continue and Finalize payloads
    - Negative Knowledge inline over separate component: ~25 lines JSX, not worth extraction
    - Collapsible neg knowledge: avoids overwhelming the decision flow with failure history
*/

import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { BuildReviewData, UserInput } from "../types";
import KnowledgeGraph from "./KnowledgeGraph";
import GapCarousel from "./GapCarousel";

interface BuildDecisionProps {
  data: BuildReviewData;
  onSubmit: (input: UserInput) => void;
}

export default function BuildDecision({ data, onSubmit }: BuildDecisionProps) {
  const { t } = useTranslation();

  // Free-text direction (when gaps=0)
  const [directionText, setDirectionText] = useState("");

  // Gap selection (lifted from GapCarousel)
  const [selectedGapIndices, setSelectedGapIndices] = useState<number[]>([]);

  // Insight card state
  const [showInsight, setShowInsight] = useState(false);
  const [insightText, setInsightText] = useState("");
  const [insightUrls, setInsightUrls] = useState<string[]>([""]);

  // Deep dive state
  const [selectedClaimId, setSelectedClaimId] = useState("");

  // Negative knowledge
  const [showNegKnowledge, setShowNegKnowledge] = useState(false);

  // Validation
  const [error, setError] = useState("");

  const gaps = data.gaps;

  // -- Handlers --

  const handleContinue = () => {
    setError("");
    const payload: UserInput = {
      type: "build_decision",
      decision: "continue",
    };
    if (selectedGapIndices.length > 0) {
      payload.selected_gaps = selectedGapIndices;
    } else if (directionText.trim()) {
      payload.continue_direction = directionText.trim();
    }
    onSubmit(payload);
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
    const payload: UserInput = { type: "build_decision", decision: "resolve" };
    if (selectedGapIndices.length > 0) {
      payload.selected_gaps = selectedGapIndices;
    }
    onSubmit(payload);
  };

  return (
    <div className="space-y-5">
      {/* Card 1: Knowledge Graph (inline) */}
      {data.graph.nodes.length > 0 && (
        <div className="bg-white border border-gray-200/80 rounded-xl shadow-md shadow-gray-200/40 overflow-hidden" style={{ height: "400px" }}>
          <KnowledgeGraph data={data.graph} />
        </div>
      )}

      {/* Card 2: Negative Knowledge (collapsed by default) */}
      {data.negative_knowledge.length > 0 && (
        <div className="bg-white border border-gray-200/80 border-l-4 border-l-red-300 rounded-xl shadow-sm">
          <button
            onClick={() => setShowNegKnowledge(!showNegKnowledge)}
            className="w-full flex items-center gap-2.5 px-5 py-4 text-sm font-semibold text-red-500 uppercase tracking-wide hover:bg-red-50/30 transition-colors"
            data-testid="neg-knowledge-toggle"
          >
            <i className="bi bi-x-octagon text-base" />
            {t("build.negativeKnowledge")}
            <span className="ml-1 text-xs font-normal text-gray-400">({data.negative_knowledge.length})</span>
            <span className={`ml-auto transition-transform duration-200 ${showNegKnowledge ? "rotate-90" : ""}`}>&#9654;</span>
          </button>
          <div className={`collapse-section ${showNegKnowledge ? 'open' : ''}`}>
            <div className="collapse-inner">
              <p className="text-xs text-gray-500 leading-relaxed px-5 mb-2">
                {t("build.negativeKnowledgeHint")}
              </p>
              <div className="px-5 pb-5 space-y-3" data-testid="neg-knowledge-list">
                {data.negative_knowledge.map((nk, i) => (
                  <div key={i} className="bg-red-50/50 border border-red-100 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-xs font-medium text-red-400 bg-red-100 px-2 py-0.5 rounded">
                        {t("build.negKnowledgeRound", { round: nk.round })}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 mb-1">{nk.claim_text}</p>
                    {nk.rejection_reason && (
                      <p className="text-xs text-red-400 italic">{nk.rejection_reason}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Card 3: Deep Dive (only when rounds remain) */}
      {!data.max_rounds_reached && (
        <div className="bg-white border border-gray-200/80 border-l-4 border-l-blue-400 rounded-xl shadow-sm p-5">
          <h3 className="flex items-center gap-2.5 text-sm font-semibold text-blue-600 uppercase tracking-wide mb-3">
            <i className="bi bi-search text-base" />
            {t("build.deepDiveTitle")}
          </h3>
          <p className="text-xs text-gray-500 leading-relaxed mb-3">
            {t("build.deepDiveHint")}
          </p>
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

      {/* Card 4: Knowledge Gaps (carousel or free-text direction) */}
      {!data.max_rounds_reached && (
        gaps.length > 0 ? (
          <GapCarousel gaps={gaps} onSelectionChange={setSelectedGapIndices} />
        ) : (
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
              className="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none placeholder-gray-400"
            />
          </div>
        )
      )}

      {/* Card 5: Insight (collapsible) */}
      <div className="bg-white border border-gray-200/80 border-l-4 border-l-indigo-400 rounded-xl shadow-sm">
        <button
          onClick={() => setShowInsight(!showInsight)}
          className="w-full flex items-center gap-2.5 px-5 py-4 text-sm font-semibold text-indigo-600 uppercase tracking-wide hover:bg-indigo-50/30 transition-colors"
        >
          <i className="bi bi-lightbulb text-base" />
          {t("build.insightCard")}
          <span className={`ml-auto transition-transform duration-200 ${showInsight ? "rotate-90" : ""}`}>&#9654;</span>
        </button>
        <div className={`collapse-section ${showInsight ? 'open' : ''}`}>
          <div className="collapse-inner">
          <div className="px-5 pb-5 space-y-3">
            <p className="text-xs text-gray-500 leading-relaxed">
              {t("build.insightHint")}
            </p>
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
          </div>
        </div>
      </div>

      {/* Card 6: Continue / Finalize */}
      <p className="text-xs text-gray-500 leading-relaxed text-center">
        {t("build.continueHint")}
      </p>
      <div className="flex gap-3">
        {!data.max_rounds_reached && (
          <button
            onClick={handleContinue}
            className="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm py-3 px-6 rounded-lg transition-all"
          >
            {t("build.continue")}
          </button>
        )}
        <button
          onClick={handleFinalize}
          className={`${data.max_rounds_reached ? "w-full" : "flex-1"} bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm py-3 px-6 rounded-lg transition-all`}
        >
          {t("build.finalize")}
        </button>
      </div>

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
