/* SessionPage — TRIZ 6-phase session UI with knowledge graph sidebar. */

import { useEffect } from "react";
import { useParams } from "react-router-dom";
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
import type { Phase, UserInput } from "../types";

export function SessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
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
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">TRIZ</h1>
            <p className="text-xs text-gray-500 font-mono">{sessionId?.slice(0, 8)}</p>
          </div>
          <ContextMeter usage={stream.contextUsage} />
        </div>
      </header>

      {/* Phase Timeline */}
      <div className="max-w-7xl mx-auto px-6 pt-6">
        <PhaseTimeline currentPhase={stream.currentPhase as Phase | null} />
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className={`grid gap-6 ${showGraph ? "grid-cols-1 lg:grid-cols-3" : "grid-cols-1"}`}>
          {/* Left: Review panels + Agent activity */}
          <div className={`space-y-6 ${showGraph ? "lg:col-span-2" : ""}`}>
            {/* Error */}
            {stream.error && (
              <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-sm text-red-300">
                {stream.error}
              </div>
            )}

            {/* Tool errors */}
            {stream.toolErrors.length > 0 && (
              <div className="space-y-1">
                {stream.toolErrors.map((te, i) => (
                  <div
                    key={i}
                    className="text-xs text-orange-300 bg-orange-900/30 border border-orange-800 rounded px-3 py-2"
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

            {/* Waiting state */}
            {showNothing && stream.isStreaming && (
              <div className="bg-gray-800 rounded-lg p-8 text-center">
                <div className="animate-pulse">
                  <div className="w-16 h-16 bg-blue-600 rounded-full mx-auto mb-4" />
                  <p className="text-gray-400">Agent is working on your investigation...</p>
                </div>
              </div>
            )}

            {/* Agent Activity Log */}
            <AgentActivity
              isStreaming={stream.isStreaming}
              agentText={stream.agentText}
              toolCalls={stream.toolCalls}
              toolErrors={stream.toolErrors}
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
