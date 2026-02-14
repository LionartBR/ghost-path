/* API Client — communicates with TRIZ backend. */

import type { Session, UserInput, SSEEvent, GraphData } from "../types";

const API_BASE = "/api/v1";

export async function createSession(problem: string, locale?: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ problem, locale }),
  });
  if (!res.ok) throw new Error(`Failed to create session: ${res.status}`);
  return res.json() as Promise<Session>;
}

export async function getSession(sessionId: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!res.ok) throw new Error(`Session not found: ${res.status}`);
  return res.json() as Promise<Session>;
}

export async function listSessions(): Promise<{
  sessions: Session[];
  pagination: { limit: number; offset: number };
}> {
  const res = await fetch(`${API_BASE}/sessions`);
  if (!res.ok) throw new Error(`Failed to list sessions: ${res.status}`);
  return res.json() as Promise<{ sessions: Session[]; pagination: { limit: number; offset: number } }>;
}

export async function getKnowledgeGraph(sessionId: string): Promise<GraphData> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/graph`);
  if (!res.ok) throw new Error(`Failed to get graph: ${res.status}`);
  return res.json() as Promise<GraphData>;
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const error = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(error.detail ?? `Failed to delete session: ${res.status}`);
  }
}

export async function cancelSession(sessionId: string): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/cancel`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(error.detail ?? `Failed to cancel session: ${res.status}`);
  }
  return res.json() as Promise<{ message: string }>;
}

export async function sendResearchDirective(
  sessionId: string,
  directiveType: string,
  query: string,
  domain: string,
): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/research-directive`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ directive_type: directiveType, query, domain }),
  });
  if (!res.ok) throw new Error(`Failed to send directive: ${res.status}`);
  return res.json() as Promise<{ status: string }>;
}

function createSSEStream(
  url: string,
  options: RequestInit,
  onEvent: (event: SSEEvent) => void,
  onError?: (error: Error) => void,
): AbortController {
  const controller = new AbortController();

  fetch(url, { ...options, signal: controller.signal })
    .then(async (res) => {
      if (!res.ok || !res.body) {
        onError?.(new Error(`Stream failed: ${res.status}`));
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          const dataLine = line.replace(/^data: /, "").trim();
          if (!dataLine) continue;
          try {
            onEvent(JSON.parse(dataLine) as SSEEvent);
          } catch {
            /* skip malformed events */
          }
        }
      }
    })
    .catch((err: unknown) => {
      if (err instanceof Error && err.name !== "AbortError") onError?.(err);
    });

  return controller;
}

export function streamSession(
  sessionId: string,
  onEvent: (event: SSEEvent) => void,
  onError?: (error: Error) => void,
): AbortController {
  return createSSEStream(
    `${API_BASE}/sessions/${sessionId}/stream`,
    {},
    onEvent,
    onError,
  );
}

export function sendUserInput(
  sessionId: string,
  input: UserInput,
  onEvent: (event: SSEEvent) => void,
  onError?: (error: Error) => void,
): AbortController {
  return createSSEStream(
    `${API_BASE}/sessions/${sessionId}/user-input`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
    onEvent,
    onError,
  );
}
