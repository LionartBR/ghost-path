/* useAgentStream — SSE consumer that dispatches events by type. */

import { useCallback, useRef, useState } from "react";
import { streamSession, sendUserInput } from "../api/client";
import type {
  SSEEvent,
  Premise,
  AskUserData,
  ContextUsage,
  UserInput,
} from "../types";

interface AgentStreamState {
  isStreaming: boolean;
  agentText: string[];
  toolCalls: { tool: string; input_preview: string }[];
  toolErrors: { tool: string; error_code: string; message: string }[];
  premises: Premise[] | null;
  askUser: AskUserData | null;
  finalSpec: string | null;
  contextUsage: ContextUsage | null;
  specDownloadUrl: string | null;
  awaitingInput: boolean;
  error: string | null;
  roundNumber: number;
}

const initialState: AgentStreamState = {
  isStreaming: false,
  agentText: [],
  toolCalls: [],
  toolErrors: [],
  premises: null,
  askUser: null,
  finalSpec: null,
  contextUsage: null,
  specDownloadUrl: null,
  awaitingInput: false,
  error: null,
  roundNumber: 1,
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
            event.data as {
              tool: string;
              error_code: string;
              message: string;
            },
          ],
        }));
        break;
      case "premises":
        setState((s) => ({
          ...s,
          premises: event.data as Premise[],
          roundNumber: s.roundNumber + (s.premises ? 1 : 0),
        }));
        break;
      case "ask_user":
        setState((s) => ({
          ...s,
          askUser: event.data as AskUserData,
        }));
        break;
      case "final_spec":
        setState((s) => ({ ...s, finalSpec: event.data as string }));
        break;
      case "context_usage":
        setState((s) => ({
          ...s,
          contextUsage: event.data as ContextUsage,
        }));
        break;
      case "spec_file_ready": {
        const d = event.data as { download_url: string };
        setState((s) => ({ ...s, specDownloadUrl: d.download_url }));
        break;
      }
      case "error":
        setState((s) => ({
          ...s,
          error: (event.data as { message: string }).message,
        }));
        break;
      case "done": {
        const d = event.data as {
          error: boolean;
          awaiting_input: boolean;
        };
        setState((s) => ({
          ...s,
          isStreaming: false,
          awaitingInput: d.awaiting_input,
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
      setState((s) => ({
        ...s,
        isStreaming: false,
        error: err.message,
      }));
    });
  }, [sessionId, handleEvent]);

  const sendInput = useCallback(
    (input: UserInput) => {
      if (!sessionId) return;
      setState((s) => ({
        ...s,
        isStreaming: true,
        premises: null,
        askUser: null,
        agentText: [],
        toolCalls: [],
        toolErrors: [],
        error: null,
      }));
      controllerRef.current = sendUserInput(
        sessionId,
        input,
        handleEvent,
        (err) => {
          setState((s) => ({
            ...s,
            isStreaming: false,
            error: err.message,
          }));
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
