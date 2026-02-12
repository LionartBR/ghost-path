/* useSession — session creation and retrieval. */

import { useState, useCallback } from "react";
import { createSession, getSession } from "../api/client";
import type { Session } from "../types";

export function useSession() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useCallback(async (problem: string) => {
    setLoading(true);
    setError(null);
    try {
      const s = await createSession(problem);
      setSession(s);
      return s;
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create session",
      );
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const load = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const s = await getSession(id);
      setSession(s);
      return s;
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load session",
      );
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { session, loading, error, create, load };
}
