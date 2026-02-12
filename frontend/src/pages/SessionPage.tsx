import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { useAgentStream } from "../hooks/useAgentStream";
import { RoundView } from "../components/RoundView";
import { AskUser } from "../components/AskUser";
import { AgentActivityIndicator } from "../components/AgentActivityIndicator";
import { ContextMeter } from "../components/ContextMeter";
import { SpecDownload } from "../components/SpecDownload";
import type { PremiseScore } from "../types";

export function SessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const stream = useAgentStream(sessionId ?? null);

  useEffect(() => {
    if (sessionId && !stream.isStreaming && !stream.awaitingInput) {
      stream.startStream();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const handleSubmitScores = (scores: PremiseScore[]) => {
    stream.sendInput({ type: "scores", scores });
  };

  const handleResolve = (winnerIndex: number) => {
    if (!stream.premises) return;
    const winner = stream.premises[winnerIndex];
    stream.sendInput({
      type: "resolved",
      winner: {
        title: winner.title,
        score: winner.score ?? null,
        index: winnerIndex,
      },
    });
  };

  const handleAskUserRespond = (response: string) => {
    stream.sendInput({ type: "ask_user_response", response });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <h1 className="text-lg font-bold text-gray-900">GhostPath</h1>
          <ContextMeter usage={stream.contextUsage} />
        </div>
      </header>

      <main className="max-w-4xl mx-auto p-6 space-y-6">
        <AgentActivityIndicator
          isStreaming={stream.isStreaming}
          toolCalls={stream.toolCalls}
          agentText={stream.agentText}
        />

        {stream.error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
            {stream.error}
          </div>
        )}

        {stream.toolErrors.length > 0 && (
          <div className="space-y-1">
            {stream.toolErrors.map((te, i) => (
              <div
                key={i}
                className="text-xs text-orange-600 bg-orange-50 rounded px-3 py-1"
              >
                [{te.error_code}] {te.tool}: {te.message}
              </div>
            ))}
          </div>
        )}

        {stream.askUser && (
          <AskUser data={stream.askUser} onRespond={handleAskUserRespond} />
        )}

        {stream.premises && !stream.finalSpec && (
          <RoundView
            premises={stream.premises}
            roundNumber={stream.roundNumber}
            onSubmitScores={handleSubmitScores}
            onResolve={handleResolve}
            isStreaming={stream.isStreaming}
          />
        )}

        <SpecDownload
          specContent={stream.finalSpec}
          downloadUrl={stream.specDownloadUrl}
        />
      </main>
    </div>
  );
}
