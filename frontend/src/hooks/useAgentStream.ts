/* useAgentStream — SSE consumer for TRIZ's 6-phase pipeline. */

import { useCallback, useRef, useState } from "react";
import { streamSession, sendUserInput } from "../api/client";
import type {
  SSEEvent,
  Claim,
  DecomposeReviewData,
  ExploreReviewData,
  BuildReviewData,
  ContextUsage,
  UserInput,
} from "../types";

interface AgentStreamState {
  isStreaming: boolean;
  agentText: string[];
  toolCalls: { tool: string; input_preview: string }[];
  toolErrors: { tool: string; error_code: string; message: string }[];

  // Phase review data
  decomposeReview: DecomposeReviewData | null;
  exploreReview: ExploreReviewData | null;
  claimsReview: Claim[] | null;
  verdictsReview: Claim[] | null;
  buildReview: BuildReviewData | null;
  knowledgeDocument: string | null;

  contextUsage: ContextUsage | null;
  awaitingInput: boolean;
  error: string | null;
  currentPhase: string | null;
}

const initialState: AgentStreamState = {
  isStreaming: false,
  agentText: [],
  toolCalls: [],
  toolErrors: [],
  decomposeReview: null,
  exploreReview: null,
  claimsReview: null,
  verdictsReview: null,
  buildReview: null,
  knowledgeDocument: null,
  contextUsage: null,
  awaitingInput: false,
  error: null,
  currentPhase: null,
};

export function useAgentStream(sessionId: string | null) {
  const [state, setState] = useState<AgentStreamState>(initialState);
  const controllerRef = useRef<AbortController | null>(null);

  const handleEvent = useCallback((event: SSEEvent) => {
    switch (event.type) {
      case "agent_text":
        setState((s) => ({
          ...s,
          agentText: [...s.agentText, event.data as string],
        }));
        break;

      case "tool_call":
        setState((s) => ({
          ...s,
          toolCalls: [
            ...s.toolCalls,
            event.data as { tool: string; input_preview: string },
          ],
        }));
        break;

      case "tool_error":
        setState((s) => ({
          ...s,
          toolErrors: [
            ...s.toolErrors,
            event.data as { tool: string; error_code: string; message: string },
          ],
        }));
        break;

      case "tool_result":
        // Display only — no state change needed
        break;

      case "review_decompose":
        setState((s) => ({
          ...s,
          decomposeReview: event.data as DecomposeReviewData,
          awaitingInput: true,
          currentPhase: "decompose",
        }));
        break;

      case "review_explore":
        setState((s) => ({
          ...s,
          exploreReview: event.data as ExploreReviewData,
          awaitingInput: true,
          currentPhase: "explore",
        }));
        break;

      case "review_claims":
        setState((s) => ({
          ...s,
          claimsReview: (event.data as { claims: Claim[] }).claims,
          awaitingInput: true,
          currentPhase: "synthesize",
        }));
        break;

      case "review_verdicts":
        setState((s) => ({
          ...s,
          verdictsReview: (event.data as { claims: Claim[] }).claims,
          awaitingInput: true,
          currentPhase: "validate",
        }));
        break;

      case "review_build":
        setState((s) => ({
          ...s,
          buildReview: event.data as BuildReviewData,
          awaitingInput: true,
          currentPhase: "build",
        }));
        break;

      case "knowledge_document":
        setState((s) => ({
          ...s,
          knowledgeDocument: (event.data as { markdown: string }).markdown,
          currentPhase: "crystallize",
        }));
        break;

      case "context_usage":
        setState((s) => ({
          ...s,
          contextUsage: event.data as ContextUsage,
        }));
        break;

      case "error":
        setState((s) => ({
          ...s,
          error: (event.data as { message: string }).message,
        }));
        break;

      case "heartbeat":
        // Keep-alive during API calls — no state change needed
        break;

      case "done": {
        const d = event.data as { error: boolean; awaiting_input: boolean };
        setState((s) => ({
          ...s,
          isStreaming: false,
          awaitingInput: s.awaitingInput || d.awaiting_input,
        }));
        break;
      }
    }
  }, []);

  const startStream = useCallback(() => {
    if (!sessionId) return;
    setState((s) => ({
      ...s,
      isStreaming: true,
      agentText: [],
      toolCalls: [],
      toolErrors: [],
      error: null,
    }));
    controllerRef.current = streamSession(sessionId, handleEvent, (err) => {
      setState((s) => ({ ...s, isStreaming: false, error: err.message }));
    });
  }, [sessionId, handleEvent]);

  const sendInput = useCallback(
    (input: UserInput) => {
      if (!sessionId) return;
      setState((s) => ({
        ...s,
        isStreaming: true,
        decomposeReview: null,
        exploreReview: null,
        claimsReview: null,
        verdictsReview: null,
        buildReview: null,
        awaitingInput: false,
        agentText: [],
        toolCalls: [],
        toolErrors: [],
        error: null,
      }));
      controllerRef.current = sendUserInput(
        sessionId, input, handleEvent,
        (err) => {
          setState((s) => ({ ...s, isStreaming: false, error: err.message }));
        },
      );
    },
    [sessionId, handleEvent],
  );

  const abort = useCallback(() => {
    controllerRef.current?.abort();
    setState((s) => ({ ...s, isStreaming: false }));
  }, []);

  return { ...state, startStream, sendInput, abort };
}
