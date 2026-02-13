import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ProblemInput } from "../components/ProblemInput";
import { useSession } from "../hooks/useSession";
import { listSessions } from "../api/client";
import type { Session } from "../types";

const STATUS_COLORS: Record<
  Session["status"],
  { bg: string; text: string }
> = {
  decomposing: { bg: "bg-indigo-50", text: "text-indigo-700" },
  exploring: { bg: "bg-blue-50", text: "text-blue-700" },
  synthesizing: { bg: "bg-teal-50", text: "text-teal-700" },
  validating: { bg: "bg-amber-50", text: "text-amber-700" },
  building: { bg: "bg-rose-50", text: "text-rose-700" },
  crystallized: { bg: "bg-green-50", text: "text-green-700" },
  cancelled: { bg: "bg-gray-100", text: "text-gray-500" },
};

export function HomePage() {
  const navigate = useNavigate();
  const { loading, error, create } = useSession();
  const [sessions, setSessions] = useState<Session[]>([]);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const data = await listSessions();
      setSessions(data.sessions);
    } catch (err) {
      console.error("Failed to load sessions:", err);
    }
  };

  const handleSubmit = async (problem: string) => {
    const session = await create(problem);
    if (session) {
      navigate(`/session/${session.id}`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        <header className="mb-12 text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">TRIZ</h1>
          <p className="text-gray-500 text-base">
            Research-grade knowledge synthesis with multi-model consensus
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <section className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Start New Investigation
            </h2>
            <ProblemInput onSubmit={handleSubmit} loading={loading} />
            {error && (
              <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            )}
          </section>

          <section className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Sessions</h2>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {sessions.length === 0 ? (
                <p className="text-gray-400 text-sm text-center py-8">
                  No sessions yet. Create one to get started.
                </p>
              ) : (
                sessions.map((session) => (
                  <button
                    key={session.id}
                    onClick={() => navigate(`/session/${session.id}`)}
                    className="w-full text-left bg-white hover:bg-gray-50 border border-gray-200 rounded-lg p-4 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <span className="text-xs font-mono text-gray-400">
                        {session.id.slice(0, 8)}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          STATUS_COLORS[session.status].bg
                        } ${STATUS_COLORS[session.status].text}`}
                      >
                        {session.status}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 line-clamp-2">
                      {session.problem}
                    </p>
                    <p className="text-xs text-gray-400 mt-2">
                      Created {new Date(session.created_at).toLocaleString()}
                    </p>
                  </button>
                ))
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
