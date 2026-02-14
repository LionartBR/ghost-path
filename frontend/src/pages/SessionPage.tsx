/* SessionPage — TRIZ 6-phase session UI with knowledge graph sidebar. */

import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAgentStream } from "../hooks/useAgentStream";
import { PhaseTimeline } from "../components/PhaseTimeline";
import { AgentActivity } from "../components/AgentActivity";
import { ContextMeter } from "../components/ContextMeter";
import { DecomposeReview } from "../components/DecomposeReview";
import { ExploreReview } from "../components/ExploreReview";
import ClaimReview from "../components/ClaimReview";
import ClaimVerdictReview from "../components/ClaimVerdictReview";
import BuildDecision from "../components/BuildDecision";
import KnowledgeGraph from "../components/KnowledgeGraph";
import SessionCompletion from "../components/SessionCompletion";
import LanguageSwitcher from "../components/LanguageSwitcher";
import { TrizMascot } from "../components/TrizMascot";
import { PhaseTransitionCard } from "../components/PhaseTransitionCard";
import type { Phase, UserInput } from "../types";

export function SessionPage() {
  const { t } = useTranslation();
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const stream = useAgentStream(sessionId ?? null);

  useEffect(() => {
    if (sessionId && !stream.isStreaming && !stream.awaitingInput) {
      stream.startStream();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const handleSubmit = (input: UserInput) => {
    stream.sendInput(input);
  };

  const showGraph =
    stream.buildReview?.graph &&
    stream.buildReview.graph.nodes.length > 0;

  const showNothing =
    !stream.decomposeReview &&
    !stream.exploreReview &&
    !stream.verdictsReview &&
    !stream.buildReview &&
    !stream.completionData;

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-slate-50">
      {/* Header */}
      <header className="relative bg-white/95 backdrop-blur-sm border-b border-gray-200/80 py-3 sticky top-0 z-20 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => void navigate("/")}
              className="text-gray-900 text-lg font-extrabold tracking-tight hover:text-indigo-600 transition-colors"
            >
              TRIZ
            </button>
            <div className="h-4 w-px bg-gray-200" />
            <span className="text-xs text-gray-400 font-mono">{sessionId?.slice(0, 8)}</span>
          </div>
          <ContextMeter usage={stream.contextUsage} />
        </div>
        <div className="absolute right-4 top-1/2 -translate-y-1/2">
          <LanguageSwitcher />
        </div>
      </header>

      {/* Phase Timeline */}
      <div className="bg-white border-b border-gray-200/60">
        <div className="max-w-7xl mx-auto px-6">
          <PhaseTimeline currentPhase={stream.currentPhase as Phase | null} />
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className={`grid gap-6 ${showGraph ? "grid-cols-1 lg:grid-cols-3" : "grid-cols-1"}`}>
          {/* Left: Review panels + Agent activity */}
          <div className={`space-y-5 ${showGraph ? "lg:col-span-2" : ""}`}>
            {/* Error */}
            {stream.error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
                {stream.error}
              </div>
            )}

            {/* Tool errors */}
            {stream.toolErrors.length > 0 && (
              <div className="space-y-1">
                {stream.toolErrors.map((te, i) => (
                  <div
                    key={i}
                    className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2"
                  >
                    <span className="font-mono font-bold">[{te.error_code}]</span>{" "}
                    <span className="font-mono">{te.tool}</span>: {te.message}
                  </div>
                ))}
              </div>
            )}

            {/* Phase header — visible as soon as phase starts, before review data arrives.
                Shown for all 6 phases; hidden once SessionCompletion replaces the crystallize header. */}
            {stream.currentPhase && !stream.completionData && (
              <div className="bg-white border border-gray-200/80 border-l-4 border-l-blue-400 rounded-xl shadow-sm p-5">
                <h2 className="text-sm font-semibold text-blue-600 uppercase tracking-wide mb-1">
                  {t(`${stream.currentPhase}.title`, { round: stream.buildReview?.round ?? 1 })}
                </h2>
                <p className="text-gray-500 text-sm">
                  {t(`${stream.currentPhase}.description`)}
                </p>
              </div>
            )}

            {/* Phase 1: Decompose Review */}
            {stream.decomposeReview && stream.awaitingInput && (
              <DecomposeReview data={stream.decomposeReview} onSubmit={handleSubmit} />
            )}

            {/* Phase 2: Explore Review */}
            {stream.exploreReview && stream.awaitingInput && (
              <ExploreReview data={stream.exploreReview} onSubmit={handleSubmit} />
            )}

            {/* Phase 3: Claims Review (fallback — normally auto-submitted) */}
            {stream.claimsReview && stream.awaitingInput && !stream.verdictsReview && (
              <ClaimReview claims={stream.claimsReview} onSubmit={handleSubmit} />
            )}

            {/* Phase 4: Unified Claim + Verdict Review */}
            {stream.verdictsReview && stream.awaitingInput && (
              <ClaimVerdictReview claims={stream.verdictsReview} onSubmit={handleSubmit} />
            )}

            {/* Phase 5: Build Decision */}
            {stream.buildReview && stream.awaitingInput && (
              <BuildDecision data={stream.buildReview} onSubmit={handleSubmit} />
            )}

            {/* Phase 6: Session Completion */}
            {stream.completionData && (
              <SessionCompletion data={stream.completionData} />
            )}

            {/* Phase Transition Card — narrative interstitial between phases */}
            {stream.phaseTransition && (
              <PhaseTransitionCard
                from={stream.phaseTransition.from}
                to={stream.phaseTransition.to}
                onDismiss={stream.dismissTransition}
              />
            )}

            {/* Waiting state — ASCII mascot with mouse interaction */}
            {showNothing && stream.isStreaming && (
              <div className="bg-white border border-gray-200/80 rounded-xl shadow-md shadow-gray-200/40 p-10 text-center">
                <div className="flex justify-center mb-5">
                  <TrizMascot />
                </div>
                <p className="text-sm font-medium animate-shimmer">{t("agent.working")}</p>
                <button
                  onClick={() => void stream.abort()}
                  className="mt-5 px-4 py-2 text-sm font-medium text-red-600 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors"
                >
                  {t("session.cancel")}
                </button>
              </div>
            )}

            {/* Agent Activity Log */}
            <AgentActivity
              isStreaming={stream.isStreaming}
              activityItems={stream.activityItems}
            />
          </div>

          {/* Right: Knowledge Graph sidebar */}
          {showGraph && (
            <div className="lg:col-span-1">
              <div className="sticky top-20" style={{ height: "calc(100vh - 8rem)" }}>
                <KnowledgeGraph data={stream.buildReview!.graph} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
