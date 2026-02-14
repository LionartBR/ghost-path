import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ProblemInput } from "../components/ProblemInput";
import LanguageSwitcher from "../components/LanguageSwitcher";
import { useSession } from "../hooks/useSession";
import { listSessions, deleteSession } from "../api/client";
import type { Session } from "../types";

const STATUS_COLORS: Record<
  Session["status"],
  { bg: string; text: string; dot: string }
> = {
  decomposing: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500" },
  exploring: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500" },
  synthesizing: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500" },
  validating: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500" },
  building: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500" },
  crystallized: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-600" },
  cancelled: { bg: "bg-gray-100", text: "text-gray-500", dot: "bg-gray-400" },
};

const PHASE_KEYS = [
  "phases.decompose",
  "phases.explore",
  "phases.synthesize",
  "phases.validate",
  "phases.build",
  "phases.crystallize",
] as const;

export function HomePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { loading, error, create } = useSession();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [exampleIndex, setExampleIndex] = useState(0);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listSessions()
      .then((data) => { if (!cancelled) setSessions(data.sessions); })
      .catch((err) => console.error("Failed to load sessions:", err));
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setExampleIndex((i) => (i + 1) % 3);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  const handleSubmit = (problem: string) => {
    void create(problem).then((session) => {
      if (session) void navigate(`/session/${session.id}`);
    });
  };

  const handleDeleteClick = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (confirmingId === sessionId) {
      setConfirmingId(null);
      const snapshot = sessions;
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      void deleteSession(sessionId).catch(() => setSessions(snapshot));
    } else {
      setConfirmingId(sessionId);
      setTimeout(() => {
        setConfirmingId((cur) => (cur === sessionId ? null : cur));
      }, 3000);
    }
  };

  const exampleProblem = t(`examples.${exampleIndex}`);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4 py-16">
      {/* Language switcher */}
      <div className="absolute top-5 right-5">
        <LanguageSwitcher />
      </div>

      <div className="w-full max-w-xl flex flex-col items-center">
        {/* Decorative gradient line */}
        <div className="w-16 h-px bg-gradient-to-r from-transparent via-blue-400 to-transparent mb-6" />

        {/* Title */}
        <h1 className="text-5xl font-extrabold tracking-tight bg-gradient-to-b from-gray-900 to-gray-600 bg-clip-text text-transparent">
          {t("app.name")}
        </h1>

        {/* Subtitle */}
        <p className="mt-4 text-gray-500 text-center text-lg leading-relaxed">
          {t("app.tagline")}
        </p>
        <p className="mt-1.5 text-gray-400 text-center text-sm">
          {t("app.subtitle")}
        </p>

        {/* Phase pipeline visualization */}
        <div className="mt-10 flex items-center gap-0">
          {PHASE_KEYS.map((key, i) => (
            <div key={key} className="flex items-center">
              <div className="flex flex-col items-center">
                <div className="w-3 h-3 rounded-full bg-blue-400/50 ring-[3px] ring-blue-100" />
                <span className="mt-2.5 text-[11px] uppercase tracking-wider text-gray-400 font-medium">
                  {t(key)}
                </span>
              </div>
              {i < PHASE_KEYS.length - 1 && (
                <div className="w-10 h-px bg-gradient-to-r from-blue-200 to-blue-100 -mt-4 mx-1.5" />
              )}
            </div>
          ))}
        </div>

        {/* Main input card */}
        <div className="mt-12 w-full bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100/80 p-7">
          <ProblemInput
            onSubmit={handleSubmit}
            loading={loading}
            exampleProblem={exampleProblem}
          />
          {error && (
            <div className="mt-4 bg-blue-50 border border-blue-200 rounded-xl p-3">
              <p className="text-blue-600 text-sm">{error}</p>
            </div>
          )}
        </div>

        {/* Recent sessions */}
        {sessions.length > 0 && (
          <div className="mt-12 w-full">
            <div className="flex items-center gap-4 mb-5">
              <div className="flex-1 h-px bg-gray-200" />
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                {t("sessions.recent")}
              </span>
              <div className="flex-1 h-px bg-gray-200" />
            </div>

            <div className="space-y-2.5">
              {sessions.map((session) => {
                const colors = STATUS_COLORS[session.status];
                return (
                  <button
                    key={session.id}
                    onClick={() => void navigate(`/session/${session.id}`)}
                    className="w-full text-left bg-white hover:bg-gray-50/80 border border-gray-200
                               rounded-xl p-4 transition-all group hover:shadow-sm"
                  >
                    <div className="flex items-start justify-between mb-1.5">
                      <p className="text-sm text-gray-700 line-clamp-2 leading-snug group-hover:text-gray-900 transition-colors">
                        {session.problem}
                      </p>
                      <div className="ml-3 shrink-0 flex items-center gap-1.5">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${colors.dot}`}
                          />
                          {t(`status.${session.status}`)}
                        </span>
                        {confirmingId === session.id ? (
                          <button
                            onClick={(e) => handleDeleteClick(e, session.id)}
                            className="animate-pulse px-2 py-0.5 rounded-full text-xs font-medium
                                       bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors"
                          >
                            {t("sessions.confirmDelete")}
                          </button>
                        ) : (
                          <button
                            onClick={(e) => handleDeleteClick(e, session.id)}
                            className="opacity-0 group-hover:opacity-100 transition-opacity
                                       w-6 h-6 flex items-center justify-center rounded-full
                                       text-gray-400 hover:text-blue-500 hover:bg-blue-50"
                            aria-label={t("sessions.delete")}
                          >
                            &times;
                          </button>
                        )}
                      </div>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      {new Date(session.created_at).toLocaleString()}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
