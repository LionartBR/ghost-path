import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ProblemInput } from "../components/ProblemInput";
import { useSession } from "../hooks/useSession";
import { listSessions } from "../api/client";
import type { Session } from "../types";

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
  decomposing: { bg: "bg-indigo-50", text: "text-indigo-700", dot: "bg-indigo-400" },
  exploring: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-400" },
  synthesizing: { bg: "bg-teal-50", text: "text-teal-700", dot: "bg-teal-400" },
  validating: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-400" },
  building: { bg: "bg-rose-50", text: "text-rose-700", dot: "bg-rose-400" },
  crystallized: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-400" },
  cancelled: { bg: "bg-gray-100", text: "text-gray-500", dot: "bg-gray-400" },
};

const EXAMPLE_PROBLEMS = [
  "How can we reduce developer onboarding from 2 weeks to 2 days?",
  "Why do 60% of ML models never reach production?",
  "How might we make remote teams as creative as co-located ones?",
];

export function HomePage() {
  const navigate = useNavigate();
  const { loading, error, create } = useSession();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [exampleIdx, setExampleIdx] = useState(0);

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setExampleIdx((i) => (i + 1) % EXAMPLE_PROBLEMS.length);
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
    <div className="min-h-screen bg-[#fafafa] flex flex-col">
      {/* Hero */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 pt-16 pb-8">
        <div className="w-full max-w-2xl text-center mb-10">
          {/* Accent line */}
          <div className="mx-auto mb-6 h-px w-16 bg-gradient-to-r from-transparent via-indigo-400 to-transparent" />

          <h1 className="text-5xl font-extrabold tracking-tight text-gray-900 mb-3">
            TRIZ
          </h1>
          <p className="text-lg text-gray-500 font-light leading-relaxed">
            Transform complex problems into structured knowledge
            <br />
            <span className="text-gray-400">through dialectical reasoning in 6 phases</span>
          </p>
        </div>

        {/* Pipeline */}
        <div className="w-full max-w-xl mb-10">
          <div className="flex items-center justify-between relative">
            {/* Connecting line */}
            <div className="absolute top-3 left-6 right-6 h-px bg-gray-200" />
            {PHASES.map((phase, i) => (
              <div key={phase} className="flex flex-col items-center relative z-10">
                <div className="w-6 h-6 rounded-full bg-white border-2 border-gray-200 flex items-center justify-center mb-2 transition-all">
                  <div className="w-2 h-2 rounded-full bg-gray-300" />
                </div>
                <span className="text-[11px] font-medium text-gray-400 tracking-wide uppercase">
                  {phase}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Main input card */}
        <div className="w-full max-w-2xl">
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-[0_1px_3px_rgba(0,0,0,0.04),0_8px_24px_rgba(0,0,0,0.03)] p-8">
            <ProblemInput
              onSubmit={handleSubmit}
              loading={loading}
              exampleProblem={EXAMPLE_PROBLEMS[exampleIdx]}
            />
            {error && (
              <div className="mt-4 bg-red-50 border border-red-200 rounded-xl p-3">
                <p className="text-red-600 text-sm">{error}</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent sessions */}
      {sessions.length > 0 && (
        <div className="w-full max-w-2xl mx-auto px-6 pb-16">
          <div className="flex items-center gap-3 mb-4">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
              Recent Sessions
            </h2>
            <div className="flex-1 h-px bg-gray-200" />
          </div>
          <div className="space-y-2">
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => navigate(`/session/${session.id}`)}
                className="w-full text-left bg-white hover:bg-gray-50/80 border border-gray-200/80
                           rounded-xl p-4 transition-all duration-150
                           hover:shadow-[0_1px_4px_rgba(0,0,0,0.04)] group"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <p className="text-sm text-gray-800 font-medium line-clamp-1 group-hover:text-gray-900 transition-colors">
                    {session.problem}
                  </p>
                  <span
                    className={`ml-3 flex-shrink-0 inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      STATUS_COLORS[session.status].bg
                    } ${STATUS_COLORS[session.status].text}`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${STATUS_COLORS[session.status].dot}`} />
                    {session.status}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-gray-400">
                  <span className="font-mono">{session.id.slice(0, 8)}</span>
                  <span>&middot;</span>
                  <span>{new Date(session.created_at).toLocaleString()}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
