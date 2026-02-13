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
  decomposing: { bg: "bg-blue-600", text: "text-blue-100" },
  exploring: { bg: "bg-purple-600", text: "text-purple-100" },
  synthesizing: { bg: "bg-indigo-600", text: "text-indigo-100" },
  validating: { bg: "bg-yellow-600", text: "text-yellow-100" },
  building: { bg: "bg-green-600", text: "text-green-100" },
  crystallized: { bg: "bg-emerald-600", text: "text-emerald-100" },
  cancelled: { bg: "bg-gray-600", text: "text-gray-100" },
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
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-6xl mx-auto">
        <header className="mb-12 text-center">
          <h1 className="text-5xl font-bold mb-2">TRIZ</h1>
          <p className="text-gray-400 text-lg">
            Research-grade knowledge synthesis with multi-model consensus
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <section className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-2xl font-semibold mb-4">
              Start New Investigation
            </h2>
            <ProblemInput onSubmit={handleSubmit} loading={loading} />
            {error && (
              <div className="mt-4 bg-red-900 bg-opacity-30 border border-red-700 rounded-lg p-3">
                <p className="text-red-300 text-sm">{error}</p>
              </div>
            )}
          </section>

          <section className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-2xl font-semibold mb-4">Recent Sessions</h2>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {sessions.length === 0 ? (
                <p className="text-gray-400 text-center py-8">
                  No sessions yet. Create one to get started.
                </p>
              ) : (
                sessions.map((session) => (
                  <button
                    key={session.id}
                    onClick={() => navigate(`/session/${session.id}`)}
                    className="w-full text-left bg-gray-900 hover:bg-gray-750 border border-gray-700 rounded-lg p-4 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <span className="text-xs font-mono text-gray-500">
                        {session.id.slice(0, 8)}
                      </span>
                      <span
                        className={`px-2 py-1 rounded text-xs font-semibold ${
                          STATUS_COLORS[session.status].bg
                        } ${STATUS_COLORS[session.status].text}`}
                      >
                        {session.status}
                      </span>
                    </div>
                    <p className="text-sm text-gray-300 line-clamp-2">
                      {session.problem}
                    </p>
                    <p className="text-xs text-gray-500 mt-2">
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
