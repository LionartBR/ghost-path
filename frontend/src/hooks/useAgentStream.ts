/* useAgentStream — SSE consumer for TRIZ's 6-phase pipeline. */

import { useCallback, useRef, useState } from "react";
import { streamSession, sendUserInput, cancelSession } from "../api/client";
import type {
  SSEEvent,
  Claim,
  CompletionData,
  DecomposeReviewData,
  ExploreReviewData,
  BuildReviewData,
  ContextUsage,
  UserInput,
  ActivityItem,
  Phase,
  PhaseTransition,
  WebSearchResult,
} from "../types";

/* ADR: derive next phase from user input type — avoids needing
   a server-emitted phase_change event for the transition card */
function getNextPhase(input: UserInput): Phase | null {
  switch (input.type) {
    case "decompose_review":
      return "explore";
    case "explore_review":
      return "synthesize";
    case "claims_review":
      return "validate";
    case "verdicts": {
      const allRejected =
        input.verdicts?.length &&
        input.verdicts.every((v) => v.verdict === "reject");
      return allRejected ? "synthesize" : "build";
    }
    case "build_decision":
      return input.decision === "resolve" ? "crystallize" : "synthesize";
    default:
      return null;
  }
}

interface AgentStreamState {
  isStreaming: boolean;
  activityItems: ActivityItem[];
  toolErrors: { tool: string; error_code: string; message: string }[];
  /* ADR: pendingClear defers activityItems reset until the first new
     agent_text arrives, so phase explanation messages stay visible
     while the user waits for the agent to respond. */
  pendingClear: boolean;

  // Phase review data
  decomposeReview: DecomposeReviewData | null;
  exploreReview: ExploreReviewData | null;
  claimsReview: Claim[] | null;
  verdictsReview: Claim[] | null;
  buildReview: BuildReviewData | null;
  knowledgeDocument: string | null;
  completionData: CompletionData | null;

  contextUsage: ContextUsage | null;
  awaitingInput: boolean;
  error: string | null;
  currentPhase: string | null;
  phaseTransition: PhaseTransition | null;
}

const initialState: AgentStreamState = {
  isStreaming: false,
  activityItems: [],
  toolErrors: [],
  pendingClear: false,
  decomposeReview: null,
  exploreReview: null,
  claimsReview: null,
  verdictsReview: null,
  buildReview: null,
  knowledgeDocument: null,
  completionData: null,
  contextUsage: {
    tokens_used: 0,
    tokens_limit: 1_000_000,
    tokens_remaining: 1_000_000,
    usage_percentage: 0,
    input_tokens: 0,
    output_tokens: 0,
  },
  awaitingInput: false,
  error: null,
  currentPhase: null,
  phaseTransition: null,
};

export function useAgentStream(sessionId: string | null) {
  const [state, setState] = useState<AgentStreamState>(initialState);
  const controllerRef = useRef<AbortController | null>(null);
  /* Guard ref: prevents StrictMode from calling startStream() twice.
     Refs persist across StrictMode's simulated unmount/remount cycle,
     so the second effect invocation sees activeRef.current === true
     and skips the duplicate SSE connection. */
  const activeRef = useRef(false);
  const handleEvent = useCallback((event: SSEEvent) => {
    switch (event.type) {
      case "agent_text": {
        const chunk = event.data as string;
        setState((s) => {
          /* If a clear is pending (user just submitted input), flush old
             items now — the new agent text replaces them naturally. */
          const items = s.pendingClear ? [] : s.activityItems;
          const cleared = s.pendingClear ? false : s.pendingClear;
          const last = items.length > 0 ? items[items.length - 1] : null;
          if (last && last.kind === "text") {
            const merged = [...items];
            merged[merged.length - 1] = { kind: "text", text: last.text + chunk };
            return { ...s, activityItems: merged, pendingClear: cleared };
          }
          return { ...s, activityItems: [...items, { kind: "text", text: chunk }], pendingClear: cleared };
        });
        break;
      }

      case "tool_call": {
        const tc = event.data as { tool: string; input_preview: string };
        setState((s) => {
          const items = s.pendingClear ? [] : s.activityItems;
          return {
            ...s,
            activityItems: [...items, { kind: "tool_call", ...tc }],
            pendingClear: false,
          };
        });
        break;
      }

      case "tool_error": {
        const te = event.data as { tool: string; error_code: string; message: string };
        setState((s) => ({
          ...s,
          toolErrors: [...s.toolErrors, te],
          activityItems: [...s.activityItems, { kind: "tool_error", ...te }],
        }));
        break;
      }

      case "tool_result":
        // Display only — no state change needed
        break;

      case "web_search_detail": {
        const detail = event.data as { query: string; results: WebSearchResult[] };
        setState((s) => {
          const items = [...s.activityItems];
          // Find matching tool_call pill (web_search with same query) and upgrade in-place
          for (let i = items.length - 1; i >= 0; i--) {
            const it = items[i];
            if (it.kind === "tool_call" && it.tool === "web_search" && it.input_preview === detail.query) {
              items[i] = {
                kind: "web_search",
                query: detail.query,
                results: detail.results,
              };
              return { ...s, activityItems: items };
            }
          }
          // No matching pill found — append as new card
          items.push({
            kind: "web_search",
            query: detail.query,
            results: detail.results,
          });
          return { ...s, activityItems: items };
        });
        break;
      }

      case "review_decompose":
        setState((s) => ({
          ...s,
          decomposeReview: event.data as DecomposeReviewData,
          awaitingInput: true,
          currentPhase: "decompose",
          phaseTransition: null,
        }));
        break;

      case "review_explore":
        setState((s) => ({
          ...s,
          exploreReview: event.data as ExploreReviewData,
          awaitingInput: true,
          currentPhase: "explore",
          phaseTransition: null,
        }));
        break;

      case "review_claims": {
        const claims = (event.data as { claims: Claim[] }).claims;
        setState((s) => ({
          ...s,
          claimsReview: claims,
          awaitingInput: true,
          currentPhase: "synthesize",
          phaseTransition: null,
        }));
        break;
      }

      case "review_verdicts":
        setState((s) => ({
          ...s,
          verdictsReview: (event.data as { claims: Claim[] }).claims,
          awaitingInput: true,
          currentPhase: "validate",
          phaseTransition: null,
        }));
        break;

      case "review_build":
        setState((s) => ({
          ...s,
          buildReview: event.data as BuildReviewData,
          awaitingInput: true,
          currentPhase: "build",
          phaseTransition: null,
        }));
        break;

      case "knowledge_document": {
        const doc = event.data as CompletionData;
        setState((s) => ({
          ...s,
          knowledgeDocument: doc.markdown,
          completionData: doc,
          currentPhase: "crystallize",
          phaseTransition: null,
        }));
        break;
      }

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
        activeRef.current = false;
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
    if (!sessionId || activeRef.current) return;
    activeRef.current = true;
    setState((s) => ({
      ...s,
      isStreaming: true,
      activityItems: [],
      toolErrors: [],
      error: null,
      /* ADR: initial stream always starts at decompose — set it immediately
         so SessionPage can render the phase header before any SSE arrives */
      currentPhase: s.currentPhase ?? "decompose",
    }));
    controllerRef.current = streamSession(sessionId, handleEvent, (err) => {
      activeRef.current = false;
      setState((s) => ({ ...s, isStreaming: false, error: err.message }));
    });
  }, [sessionId, handleEvent]);

  const sendInput = useCallback(
    (input: UserInput) => {
      if (!sessionId) return;
      activeRef.current = true;
      const nextPhase = getNextPhase(input);
      setState((s) => ({
        ...s,
        isStreaming: true,
        decomposeReview: null,
        exploreReview: null,
        claimsReview: null,
        verdictsReview: null,
        buildReview: null,
        completionData: null,
        awaitingInput: false,
        pendingClear: true,
        toolErrors: [],
        error: null,
        /* ADR: set currentPhase immediately so the phase header updates
           before the agent responds — the review event will confirm later */
        currentPhase: nextPhase ?? s.currentPhase,
        phaseTransition:
          nextPhase && s.currentPhase
            ? { from: s.currentPhase as Phase, to: nextPhase }
            : null,
      }));
      controllerRef.current = sendUserInput(
        sessionId, input, handleEvent,
        (err) => {
          activeRef.current = false;
          setState((s) => ({ ...s, isStreaming: false, error: err.message }));
        },
      );
    },
    [sessionId, handleEvent],
  );

  const abort = useCallback(async () => {
    activeRef.current = false;
    controllerRef.current?.abort();
    if (sessionId) {
      try {
        await cancelSession(sessionId);
      } catch (err) {
        // Best-effort: stream already aborted client-side
        console.error("Failed to cancel session:", err);
      }
    }
    setState((s) => ({ ...s, isStreaming: false }));
  }, [sessionId]);

  const dismissTransition = useCallback(() => {
    setState((s) => ({ ...s, phaseTransition: null }));
  }, []);

  return { ...state, startStream, sendInput, abort, dismissTransition };
}
