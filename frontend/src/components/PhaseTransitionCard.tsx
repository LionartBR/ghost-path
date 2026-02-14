/**PhaseTransitionCard — persistent narrative card between TRIZ pipeline phases.
 *
 * Invariants:
 *   - Stays visible until the next phase transition or user dismisses
 *   - Enter animation plays once on mount
 *   - Colors match PhaseTimeline's per-phase palette
 *
 * Design Decisions:
 *   - Persistent display (ADR: user requested cards not auto-dismiss)
 *   - Uses "from" phase to distinguish first synthesize entry from round 2+ return
 */

import React, { useEffect, useState } from "react";
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
  border: string; bg: string; label: string;
}> = {
  decompose: {
    border: "border-l-blue-500", bg: "bg-blue-50/80",
    label: "text-blue-600",
  },
  explore: {
    border: "border-l-blue-500", bg: "bg-blue-50/80",
    label: "text-blue-600",
  },
  synthesize: {
    border: "border-l-blue-500", bg: "bg-blue-50/80",
    label: "text-blue-600",
  },
  validate: {
    border: "border-l-blue-500", bg: "bg-blue-50/80",
    label: "text-blue-600",
  },
  build: {
    border: "border-l-blue-500", bg: "bg-blue-50/80",
    label: "text-blue-600",
  },
  crystallize: {
    border: "border-l-blue-500", bg: "bg-blue-50/80",
    label: "text-blue-600",
  },
};

const ENTER_MS = 400;

export const PhaseTransitionCard: React.FC<PhaseTransitionCardProps> = ({
  from,
  to,
  onDismiss,
}) => {
  const { t } = useTranslation();
  const [entered, setEntered] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setEntered(true), ENTER_MS);
    return () => clearTimeout(timer);
  }, []);

  const style = PHASE_STYLE[to];
  const phaseNum = PHASE_INDEX[to];

  /* ADR: "returning to synthesize from build" has a distinct narrative
     from first entry — it's a new round, not a new phase */
  const narrativeKey =
    to === "synthesize" && from === "build"
      ? "transition.toSynthesizeReturn"
      : `transition.to${to.charAt(0).toUpperCase() + to.slice(1)}`;

  const animClass = entered ? "" : "animate-phase-enter";

  return (
    <div
      className={`
        ${animClass} overflow-hidden rounded-xl border-l-4
        ${style.border} ${style.bg}
        shadow-md shadow-gray-200/40
      `}
    >
      <div className="px-5 py-4 flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div
            className={`text-xs font-semibold uppercase tracking-wider ${style.label} mb-1.5`}
          >
            {phaseNum} &middot; {t(`phases.${to}`)}
          </div>
          <p className="text-sm text-gray-700 leading-relaxed">
            {t(narrativeKey)}
          </p>
        </div>
        <button
          onClick={onDismiss}
          className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors mt-0.5"
          aria-label="Dismiss"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
};
