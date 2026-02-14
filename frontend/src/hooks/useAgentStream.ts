/* useAgentStream — SSE consumer for TRIZ's 6-phase pipeline. */

import { useCallback, useEffect, useRef, useState } from "react";
import { streamSession, sendUserInput, cancelSession, sendResearchDirective } from "../api/client";
import type {
  SSEEvent,
  Claim,
  ClaimFeedback,
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
    case "verdicts":
      return "build";
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
  decomposeReview: null,
  exploreReview: null,
  claimsReview: null,
  verdictsReview: null,
  buildReview: null,
  knowledgeDocument: null,
  completionData: null,
  contextUsage: null,
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
  /* ADR: auto-submit Phase 3 claims review so the user sees only the
     unified verdict UI (Phase 4). Claims are stored here when the
     review_claims event arrives; a useEffect fires the auto-submit
     once the stream settles (isStreaming=false). */
  const autoSubmitClaimsRef = useRef<Claim[] | null>(null);

  const handleEvent = useCallback((event: SSEEvent) => {
    switch (event.type) {
      case "agent_text": {
        const chunk = event.data as string;
        setState((s) => {
          const items = s.activityItems;
          const last = items.length > 0 ? items[items.length - 1] : null;
          if (last && last.kind === "text") {
            const merged = [...items];
            merged[merged.length - 1] = { kind: "text", text: last.text + chunk };
            return { ...s, activityItems: merged };
          }
          return { ...s, activityItems: [...items, { kind: "text", text: chunk }] };
        });
        break;
      }

      case "tool_call": {
        const tc = event.data as { tool: string; input_preview: string };
        setState((s) => ({
          ...s,
          activityItems: [...s.activityItems, { kind: "tool_call", ...tc }],
        }));
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
                directive_sent: false,
              };
              return { ...s, activityItems: items };
            }
          }
          // No matching pill found — append as new card
          items.push({
            kind: "web_search",
            query: detail.query,
            results: detail.results,
            directive_sent: false,
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
        autoSubmitClaimsRef.current = claims;
        setState((s) => ({
          ...s,
          claimsReview: claims,
          currentPhase: "synthesize",
          phaseTransition: null,
          /* awaitingInput deliberately NOT set — auto-submit fires via useEffect */
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
        const hasAutoSubmitPending = autoSubmitClaimsRef.current !== null;
        /* Clear auto-submit on error so the useEffect fallback doesn't fire
           against a broken stream — user sees the manual ClaimReview instead. */
        if (d.error) {
          autoSubmitClaimsRef.current = null;
        }
        setState((s) => ({
          ...s,
          isStreaming: false,
          awaitingInput: hasAutoSubmitPending && !d.error
            ? s.awaitingInput
            : s.awaitingInput || d.awaiting_input,
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
        activityItems: [],
        toolErrors: [],
        error: null,
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

  /* Auto-submit Phase 3 claims review once the stream finishes.
     Sends default feedback (all evidence_valid: true) so the pipeline
     continues to Phase 4 (VALIDATE) without user interaction.
     Fallback: on failure, shows the manual ClaimReview UI. */
  useEffect(() => {
    if (state.isStreaming || !autoSubmitClaimsRef.current || !sessionId) return;
    const claims = autoSubmitClaimsRef.current;
    autoSubmitClaimsRef.current = null;
    const claim_feedback: ClaimFeedback[] = claims.map((_, i) => ({
      claim_index: i,
      evidence_valid: true,
    }));
    try {
      sendInput({ type: "claims_review", claim_feedback });
    } catch {
      /* Fallback: show manual ClaimReview if auto-submit fails */
      setState((s) => ({ ...s, awaitingInput: true }));
    }
  }, [state.isStreaming, sessionId, sendInput]);

  const abort = useCallback(async () => {
    activeRef.current = false;
    autoSubmitClaimsRef.current = null;
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

  const sendDirective = useCallback(
    (directiveType: "explore_more" | "skip_domain", query: string, domain: string) => {
      if (!sessionId) return;
      sendResearchDirective(sessionId, directiveType, query, domain).catch(
        (err) => console.error("Failed to send directive:", err),
      );
      // Mark matching web_search item as directive_sent
      setState((s) => {
        const items = s.activityItems.map((it) =>
          it.kind === "web_search" && it.query === query
            ? { ...it, directive_sent: true }
            : it,
        );
        return { ...s, activityItems: items };
      });
    },
    [sessionId],
  );

  return { ...state, startStream, sendInput, abort, dismissTransition, sendDirective };
}
