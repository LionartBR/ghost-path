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

/* ADR: removed per-phase color map — all cards now follow the standard
   blue-accent card style used across all review components */

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

  const phaseNum = PHASE_INDEX[to];

  /* ADR: "returning to synthesize from build" has a distinct narrative
     from first entry — it's a new round, not a new phase */
  const narrativeKey =
    to === "synthesize" && from === "build"
      ? "transition.toSynthesizeReturn"
      : to === "synthesize" && from === "validate"
        ? "transition.toSynthesizeRejected"
        : `transition.to${to.charAt(0).toUpperCase() + to.slice(1)}`;

  const animClass = entered ? "" : "animate-phase-enter";

  return (
    <div
      className={`${animClass} bg-white border border-gray-200/80 border-l-4 border-l-blue-400 rounded-xl shadow-sm p-5`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-1.5">
            {phaseNum} &middot; {t(`phases.${to}`)}
          </div>
          <p className="text-gray-500 text-sm leading-relaxed">
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
