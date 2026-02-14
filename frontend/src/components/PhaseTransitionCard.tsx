/**PhaseTransitionCard — narrative interstitial between TRIZ pipeline phases.
 *
 * Invariants:
 *   - Auto-dismisses after ~4.5s (0.4s enter + 3.5s hold + 0.6s exit)
 *   - Never blocks user interaction (renders above AgentActivity)
 *   - Colors match PhaseTimeline's per-phase palette
 *
 * Design Decisions:
 *   - Self-contained lifecycle via setTimeout chain (ADR: simpler than CSS animation-end events)
 *   - Progress bar fills over total duration, giving visual cue of remaining time
 *   - Uses "from" phase to distinguish first synthesize entry from round 2+ return
 */

import React, { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { Phase } from "../types";

interface PhaseTransitionCardProps {
  from: Phase;
  to: Phase;
  onDismiss: () => void;
}

const PHASE_INDEX: Record<Phase, number> = {
  decompose: 1,
  explore: 2,
  synthesize: 3,
  validate: 4,
  build: 5,
  crystallize: 6,
};

/* ADR: color palette mirrors PhaseTimeline so the transition card
   visually "belongs" to the incoming phase's identity */
const PHASE_STYLE: Record<Phase, {
  border: string; bg: string; label: string; bar: string;
}> = {
  decompose: {
    border: "border-l-indigo-500", bg: "bg-indigo-50/80",
    label: "text-indigo-600", bar: "bg-indigo-400",
  },
  explore: {
    border: "border-l-blue-500", bg: "bg-blue-50/80",
    label: "text-blue-600", bar: "bg-blue-400",
  },
  synthesize: {
    border: "border-l-teal-500", bg: "bg-teal-50/80",
    label: "text-teal-600", bar: "bg-teal-400",
  },
  validate: {
    border: "border-l-amber-500", bg: "bg-amber-50/80",
    label: "text-amber-600", bar: "bg-amber-400",
  },
  build: {
    border: "border-l-rose-500", bg: "bg-rose-50/80",
    label: "text-rose-600", bar: "bg-rose-400",
  },
  crystallize: {
    border: "border-l-slate-500", bg: "bg-slate-50/80",
    label: "text-slate-600", bar: "bg-slate-400",
  },
};

type Stage = "entering" | "visible" | "exiting" | "done";

const ENTER_MS = 400;
const HOLD_MS = 3500;
const EXIT_MS = 600;
const TOTAL_MS = ENTER_MS + HOLD_MS + EXIT_MS;

export const PhaseTransitionCard: React.FC<PhaseTransitionCardProps> = ({
  from,
  to,
  onDismiss,
}) => {
  const { t } = useTranslation();
  const [stage, setStage] = useState<Stage>("entering");
  const dismissRef = useRef(onDismiss);
  useEffect(() => { dismissRef.current = onDismiss; });

  useEffect(() => {
    const timers = [
      setTimeout(() => setStage("visible"), ENTER_MS),
      setTimeout(() => setStage("exiting"), ENTER_MS + HOLD_MS),
      setTimeout(() => {
        setStage("done");
        dismissRef.current();
      }, TOTAL_MS),
    ];
    return () => timers.forEach(clearTimeout);
  }, []);

  if (stage === "done") return null;

  const style = PHASE_STYLE[to];
  const phaseNum = PHASE_INDEX[to];

  /* ADR: "returning to synthesize from build" has a distinct narrative
     from first entry — it's a new round, not a new phase */
  const narrativeKey =
    to === "synthesize" && from === "build"
      ? "transition.toSynthesizeReturn"
      : `transition.to${to.charAt(0).toUpperCase() + to.slice(1)}`;

  const animClass =
    stage === "entering"
      ? "animate-phase-enter"
      : stage === "exiting"
        ? "animate-phase-exit"
        : "";

  return (
    <div
      className={`
        ${animClass} overflow-hidden rounded-xl border-l-4
        ${style.border} ${style.bg}
        shadow-md shadow-gray-200/40
      `}
    >
      <div className="px-5 py-4">
        <div
          className={`text-xs font-semibold uppercase tracking-wider ${style.label} mb-1.5`}
        >
          {phaseNum} &middot; {t(`phases.${to}`)}
        </div>
        <p className="text-sm text-gray-700 leading-relaxed">
          {t(narrativeKey)}
        </p>
      </div>
      <div className="h-0.5 bg-gray-200/50">
        <div
          className={`h-full ${style.bar} opacity-60`}
          style={{
            animation: `phase-progress ${TOTAL_MS / 1000}s linear forwards`,
          }}
        />
      </div>
    </div>
  );
};
