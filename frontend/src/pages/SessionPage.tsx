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
import VerdictPanel from "../components/VerdictPanel";
import BuildDecision from "../components/BuildDecision";
import KnowledgeGraph from "../components/KnowledgeGraph";
import KnowledgeDocument from "../components/KnowledgeDocument";
import LanguageSwitcher from "../components/LanguageSwitcher";
import { TrizMascot } from "../components/TrizMascot";
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
    !stream.claimsReview &&
    !stream.verdictsReview &&
    !stream.buildReview &&
    !stream.knowledgeDocument;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate("/")}
              className="text-gray-900 text-lg font-bold tracking-tight hover:text-indigo-600 transition-colors"
            >
              TRIZ
            </button>
            <span className="text-xs text-gray-400 font-mono">{sessionId?.slice(0, 8)}</span>
          </div>
          <div className="flex items-center gap-3">
            {stream.isStreaming && (
              <button
                onClick={() => stream.abort()}
                className="px-3 py-1.5 text-sm font-medium text-red-600 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors"
              >
                {t("session.cancel")}
              </button>
            )}
            <LanguageSwitcher />
            <ContextMeter usage={stream.contextUsage} />
          </div>
        </div>
      </header>

      {/* Phase Timeline */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6">
          <PhaseTimeline currentPhase={stream.currentPhase as Phase | null} />
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-6">
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

            {/* Phase 1: Decompose Review */}
            {stream.decomposeReview && stream.awaitingInput && (
              <DecomposeReview data={stream.decomposeReview} onSubmit={handleSubmit} />
            )}

            {/* Phase 2: Explore Review */}
            {stream.exploreReview && stream.awaitingInput && (
              <ExploreReview data={stream.exploreReview} onSubmit={handleSubmit} />
            )}

            {/* Phase 3: Claims Review */}
            {stream.claimsReview && stream.awaitingInput && (
              <ClaimReview claims={stream.claimsReview} onSubmit={handleSubmit} />
            )}

            {/* Phase 4: Verdicts */}
            {stream.verdictsReview && stream.awaitingInput && (
              <VerdictPanel claims={stream.verdictsReview} onSubmit={handleSubmit} />
            )}

            {/* Phase 5: Build Decision */}
            {stream.buildReview && stream.awaitingInput && (
              <BuildDecision data={stream.buildReview} onSubmit={handleSubmit} />
            )}

            {/* Phase 6: Knowledge Document */}
            {stream.knowledgeDocument && (
              <KnowledgeDocument markdown={stream.knowledgeDocument} />
            )}

            {/* Waiting state — ASCII mascot with mouse interaction */}
            {showNothing && stream.isStreaming && (
              <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-8 text-center">
                <div className="flex justify-center mb-4">
                  <TrizMascot />
                </div>
                <p className="text-gray-500 text-sm">{t("agent.working")}</p>
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
              <div className="sticky top-6">
                <KnowledgeGraph data={stream.buildReview!.graph} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
