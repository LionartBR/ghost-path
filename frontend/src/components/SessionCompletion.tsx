/* SessionCompletion — celebration screen after CRYSTALLIZE phase.

Invariants:
    - Renders hero + stats + graph + document in single scrollable page
    - Reuses FlowGraph and KnowledgeDocument components (no duplication)
    - Stats grid animates with staggered fade-in delays

Design Decisions:
    - StatCard is private (not exported) — only used here (ADR: no premature abstraction)
    - Duration formatting handles hours/minutes/unknown gracefully
    - Graph section only renders when nodes exist
    - Hero shows agent-generated problem_summary (falls back to raw problem)
    - Semantic stat colors: emerald=validated, rose=rejected, amber=qualified, etc.
    - No max-w-4xl — component fills parent grid column like all other phases
    - Micro-animations: hero-enter, glow-pulse, badge-pop, divider-reveal, section-rise, stat hover
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
      className="bg-white rounded-xl border border-gray-200/80 p-4 text-center shadow-sm
        animate-stat-count-up opacity-0
        hover:scale-105 hover:shadow-md hover:border-gray-300/80
        active:scale-100 transition-all duration-200 cursor-default"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className={`text-3xl font-extrabold ${color}`}>{value}</div>
      <div className="text-xs text-gray-500 mt-1 font-medium">{label}</div>
    </div>
  );
}

export default function SessionCompletion({ data }: SessionCompletionProps) {
  const { t } = useTranslation();
  const { stats, graph, markdown } = data;
  const heroText = data.problem_summary ?? data.problem;
  const hasGraph = graph.nodes.length > 0;

  return (
    <div className="w-full space-y-6">
      {/* Hero Section — scale+fade entrance */}
      <div className="animate-hero-enter bg-gray-50 border border-gray-200 rounded-2xl p-8 text-gray-900 shadow-md">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-12 h-12 bg-emerald-100 ring-1 ring-emerald-300/60 rounded-xl flex items-center justify-center animate-glow-pulse">
            <svg className="w-7 h-7 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-extrabold tracking-tight text-gray-900">
              {t("completion.hero.title")}
            </h1>
            <p className="mt-2 text-gray-500 text-sm leading-relaxed line-clamp-2">
              {heroText}
            </p>
          </div>
        </div>
        <div className="flex gap-3 mt-6">
          <span
            className="animate-badge-pop inline-flex items-center gap-1.5 px-3 py-1 bg-gray-200/60 hover:bg-gray-200 text-gray-700 rounded-full text-xs font-medium transition-colors duration-200"
            style={{ animationDelay: "300ms" }}
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {t("completion.hero.duration")}: {formatDuration(stats.duration_seconds, t)}
          </span>
          <span
            className="animate-badge-pop inline-flex items-center gap-1.5 px-3 py-1 bg-gray-200/60 hover:bg-gray-200 text-gray-700 rounded-full text-xs font-medium transition-colors duration-200"
            style={{ animationDelay: "420ms" }}
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {stats.total_rounds} {t("completion.hero.rounds")}
          </span>
        </div>
      </div>

      {/* Gold accent divider — reveals from center */}
      <div
        className="h-px bg-gradient-to-r from-transparent via-emerald-400/40 to-transparent animate-divider-reveal"
        style={{ animationDelay: "400ms" }}
      />

      {/* Stats Grid — semantic colors, hover lift */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard value={stats.claims_validated} label={t("completion.stats.claimsValidated")} color="text-emerald-600" delay={500} />
        <StatCard value={stats.claims_rejected} label={t("completion.stats.claimsRejected")} color="text-rose-500" delay={560} />
        <StatCard value={stats.claims_qualified} label={t("completion.stats.claimsQualified")} color="text-amber-500" delay={620} />
        <StatCard value={stats.evidence_collected} label={t("completion.stats.evidenceCollected")} color="text-blue-600" delay={680} />
        <StatCard value={stats.analogies_used} label={t("completion.stats.analogiesUsed")} color="text-violet-500" delay={740} />
        <StatCard value={stats.contradictions_found} label={t("completion.stats.contradictions")} color="text-orange-500" delay={800} />
        <StatCard value={stats.fundamentals_identified} label={t("completion.stats.fundamentals")} color="text-slate-600" delay={860} />
        <StatCard value={stats.assumptions_examined} label={t("completion.stats.assumptions")} color="text-teal-500" delay={920} />
      </div>

      {/* Knowledge Graph — rises in after stats */}
      {hasGraph && (
        <div
          className="animate-section-rise bg-white border border-gray-200/80 rounded-xl shadow-md shadow-gray-200/40 overflow-hidden hover:shadow-lg transition-shadow duration-300"
          style={{ animationDelay: "1000ms" }}
        >
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

      {/* Knowledge Document — rises in last */}
      <div
        className="animate-section-rise"
        style={{ animationDelay: hasGraph ? "1200ms" : "1000ms" }}
      >
        <KnowledgeDocument markdown={markdown} />
      </div>
    </div>
  );
}
