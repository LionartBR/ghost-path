/* SessionCompletion — celebration screen after CRYSTALLIZE phase.

Invariants:
    - Renders hero + stats + graph + document in single scrollable page
    - Reuses FlowGraph and KnowledgeDocument components (no duplication)
    - Stats grid animates with staggered fade-in delays

Design Decisions:
    - StatCard is private (not exported) — only used here (ADR: no premature abstraction)
    - Duration formatting handles hours/minutes/unknown gracefully
    - Graph section only renders when nodes exist
*/

import { useTranslation } from "react-i18next";
import FlowGraph from "./graph/FlowGraph";
import KnowledgeDocument from "./KnowledgeDocument";
import type { CompletionData } from "../types";

interface SessionCompletionProps {
  data: CompletionData;
}

function formatDuration(
  seconds: number | undefined,
  t: (key: string, opts?: Record<string, unknown>) => string,
): string {
  if (seconds == null) return t("completion.durationUnknown");
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) {
    return t("completion.durationHours", { hours, minutes });
  }
  return t("completion.durationMinutes", { minutes: minutes || 1 });
}

interface StatCardProps {
  value: number;
  label: string;
  color: string;
  delay: number;
}

function StatCard({ value, label, color, delay }: StatCardProps) {
  return (
    <div
      className="bg-white rounded-xl border border-gray-200/80 p-4 text-center shadow-sm animate-stat-count-up opacity-0"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className={`text-3xl font-extrabold ${color}`}>{value}</div>
      <div className="text-xs text-gray-500 mt-1 font-medium">{label}</div>
    </div>
  );
}

export default function SessionCompletion({ data }: SessionCompletionProps) {
  const { t } = useTranslation();
  const { stats, graph, problem, markdown } = data;
  const hasGraph = graph.nodes.length > 0;

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 animate-fade-in">
      {/* Hero Section */}
      <div className="bg-gradient-to-br from-indigo-600 via-indigo-700 to-purple-700 rounded-2xl p-8 text-white shadow-xl shadow-indigo-200/50">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
            <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-extrabold tracking-tight">
              {t("completion.hero.title")}
            </h1>
            <p className="mt-2 text-indigo-100 text-sm leading-relaxed line-clamp-3">
              {problem}
            </p>
          </div>
        </div>
        <div className="flex gap-3 mt-6">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-white/15 rounded-full text-xs font-medium">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {t("completion.hero.duration")}: {formatDuration(stats.duration_seconds, t)}
          </span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-white/15 rounded-full text-xs font-medium">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {stats.total_rounds} {t("completion.hero.rounds")}
          </span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard value={stats.claims_validated} label={t("completion.stats.claimsValidated")} color="text-green-600" delay={100} />
        <StatCard value={stats.claims_rejected} label={t("completion.stats.claimsRejected")} color="text-red-500" delay={150} />
        <StatCard value={stats.claims_qualified} label={t("completion.stats.claimsQualified")} color="text-amber-500" delay={200} />
        <StatCard value={stats.evidence_collected} label={t("completion.stats.evidenceCollected")} color="text-blue-600" delay={250} />
        <StatCard value={stats.analogies_used} label={t("completion.stats.analogiesUsed")} color="text-purple-600" delay={300} />
        <StatCard value={stats.contradictions_found} label={t("completion.stats.contradictions")} color="text-pink-600" delay={350} />
        <StatCard value={stats.fundamentals_identified} label={t("completion.stats.fundamentals")} color="text-cyan-600" delay={400} />
        <StatCard value={stats.assumptions_examined} label={t("completion.stats.assumptions")} color="text-teal-600" delay={450} />
      </div>

      {/* Knowledge Graph */}
      {hasGraph && (
        <div className="bg-white border border-gray-200/80 rounded-xl shadow-md shadow-gray-200/40 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">{t("completion.graph.title")}</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              {t("completion.graph.description", {
                nodes: stats.graph_nodes,
                edges: stats.graph_edges,
              })}
            </p>
          </div>
          <div style={{ height: 500 }}>
            <FlowGraph data={graph} />
          </div>
        </div>
      )}

      {/* Knowledge Document */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-3">
          {t("completion.document.title")}
        </h2>
        <KnowledgeDocument markdown={markdown} />
      </div>
    </div>
  );
}
