/* useSession — session creation and retrieval. */

import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { createSession, getSession } from "../api/client";
import type { Session } from "../types";

export function useSession() {
  const { t } = useTranslation();
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
        err instanceof Error ? err.message : t("errors.createSession"),
      );
      return null;
    } finally {
      setLoading(false);
    }
  }, [t]);

  const load = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const s = await getSession(id);
      setSession(s);
      return s;
    } catch (err) {
      setError(
        err instanceof Error ? err.message : t("errors.loadSession"),
      );
      return null;
    } finally {
      setLoading(false);
    }
  }, [t]);

  return { session, loading, error, create, load };
}
