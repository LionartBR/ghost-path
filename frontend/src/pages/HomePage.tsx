import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ProblemInput } from "../components/ProblemInput";
import { useSession } from "../hooks/useSession";
import { listSessions } from "../api/client";
import type { Session } from "../types";

const EXAMPLE_PROBLEMS = [
  "How can we reduce developer onboarding from 2 weeks to 2 days?",
  "How might we make renewable energy storage cost-competitive with fossil fuels?",
  "How can distributed teams maintain innovation speed without co-location?",
];

const PHASES = [
  "Decompose",
  "Explore",
  "Synthesize",
  "Validate",
  "Build",
  "Crystallize",
];

const STATUS_COLORS: Record<
  Session["status"],
  { bg: string; text: string; dot: string }
> = {
  decomposing: { bg: "bg-indigo-50", text: "text-indigo-700", dot: "bg-indigo-500" },
  exploring: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500" },
  synthesizing: { bg: "bg-teal-50", text: "text-teal-700", dot: "bg-teal-500" },
  validating: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500" },
  building: { bg: "bg-rose-50", text: "text-rose-700", dot: "bg-rose-500" },
  crystallized: { bg: "bg-green-50", text: "text-green-700", dot: "bg-green-500" },
  cancelled: { bg: "bg-gray-100", text: "text-gray-500", dot: "bg-gray-400" },
};

export function HomePage() {
  const navigate = useNavigate();
  const { loading, error, create } = useSession();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [exampleIndex, setExampleIndex] = useState(0);

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setExampleIndex((i) => (i + 1) % EXAMPLE_PROBLEMS.length);
    }, 4000);
    return () => clearInterval(timer);
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
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4 py-16">
      <div className="w-full max-w-xl flex flex-col items-center">
        {/* Decorative gradient line */}
        <div className="w-16 h-px bg-gradient-to-r from-transparent via-indigo-400 to-transparent mb-6" />

        {/* Title */}
        <h1 className="text-5xl font-bold text-gray-900 tracking-tight">
          TRIZ
        </h1>

        {/* Subtitle */}
        <p className="mt-3 text-gray-500 text-center text-lg leading-relaxed">
          Transform complex problems into structured knowledge
        </p>
        <p className="text-gray-400 text-center text-sm">
          through dialectical reasoning in 6 phases
        </p>

        {/* Phase pipeline visualization */}
        <div className="mt-8 flex items-center gap-0">
          {PHASES.map((phase, i) => (
            <div key={phase} className="flex items-center">
              <div className="flex flex-col items-center">
                <div className="w-2.5 h-2.5 rounded-full bg-indigo-300" />
                <span className="mt-2 text-[11px] uppercase tracking-wider text-gray-400 font-medium">
                  {phase}
                </span>
              </div>
              {i < PHASES.length - 1 && (
                <div className="w-8 h-px bg-gray-300 -mt-4 mx-1" />
              )}
            </div>
          ))}
        </div>

        {/* Main input card */}
        <div className="mt-10 w-full bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <ProblemInput
            onSubmit={handleSubmit}
            loading={loading}
            exampleProblem={EXAMPLE_PROBLEMS[exampleIndex]}
          />
          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 rounded-xl p-3">
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          )}
        </div>

        {/* Recent sessions */}
        {sessions.length > 0 && (
          <div className="mt-12 w-full">
            <div className="flex items-center gap-4 mb-5">
              <div className="flex-1 h-px bg-gray-200" />
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                Recent Sessions
              </span>
              <div className="flex-1 h-px bg-gray-200" />
            </div>

            <div className="space-y-2.5">
              {sessions.map((session) => {
                const colors = STATUS_COLORS[session.status];
                return (
                  <button
                    key={session.id}
                    onClick={() => navigate(`/session/${session.id}`)}
                    className="w-full text-left bg-white hover:bg-gray-50 border border-gray-200
                               rounded-xl p-4 transition-all group"
                  >
                    <div className="flex items-start justify-between mb-1.5">
                      <p className="text-sm text-gray-700 line-clamp-2 leading-snug group-hover:text-gray-900 transition-colors">
                        {session.problem}
                      </p>
                      <span
                        className={`ml-3 shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${colors.dot}`}
                        />
                        {session.status}
                      </span>
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
