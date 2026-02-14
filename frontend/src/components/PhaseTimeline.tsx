import React from "react";
import { useTranslation } from "react-i18next";
import type { Phase } from "../types";

interface PhaseTimelineProps {
  currentPhase: Phase | null;
}

const PHASES: { name: Phase; key: string; color: string }[] = [
  { name: "decompose", key: "phases.decompose", color: "indigo" },
  { name: "explore", key: "phases.explore", color: "blue" },
  { name: "synthesize", key: "phases.synthesize", color: "teal" },
  { name: "validate", key: "phases.validate", color: "amber" },
  { name: "build", key: "phases.build", color: "rose" },
  { name: "crystallize", key: "phases.crystallize", color: "slate" },
];

const getPhaseIndex = (phase: Phase | null): number => {
  if (!phase) return -1;
  return PHASES.findIndex((p) => p.name === phase);
};

const ACTIVE_BG: Record<string, string> = {
  indigo: "bg-indigo-500",
  blue: "bg-blue-500",
  teal: "bg-teal-500",
  amber: "bg-amber-500",
  rose: "bg-rose-500",
  slate: "bg-slate-500",
};

const ACTIVE_RING: Record<string, string> = {
  indigo: "ring-indigo-200",
  blue: "ring-blue-200",
  teal: "ring-teal-200",
  amber: "ring-amber-200",
  rose: "ring-rose-200",
  slate: "ring-slate-200",
};

const FUTURE_BG: Record<string, string> = {
  indigo: "bg-indigo-100",
  blue: "bg-blue-100",
  teal: "bg-teal-100",
  amber: "bg-amber-100",
  rose: "bg-rose-100",
  slate: "bg-slate-100",
};

const LABEL_COLOR: Record<string, string> = {
  indigo: "text-indigo-700",
  blue: "text-blue-700",
  teal: "text-teal-700",
  amber: "text-amber-700",
  rose: "text-rose-700",
  slate: "text-slate-700",
};

export const PhaseTimeline: React.FC<PhaseTimelineProps> = ({ currentPhase }) => {
  const { t } = useTranslation();
  const currentIndex = getPhaseIndex(currentPhase);

  return (
    <div className="w-full py-4 px-4">
      <div className="flex items-center justify-between">
        {PHASES.map((phase, index) => {
          const state =
            index < currentIndex
              ? "complete"
              : index === currentIndex
              ? "active"
              : "future";

          const isLast = index === PHASES.length - 1;

          return (
            <React.Fragment key={phase.name}>
              <div className="flex flex-col items-center">
                <div
                  className={`
                    w-9 h-9 rounded-full flex items-center justify-center
                    text-sm font-semibold transition-all duration-300
                    ${state === "complete" ? "bg-green-500 text-white" : ""}
                    ${state === "active" ? `${ACTIVE_BG[phase.color]} text-white ring-4 ${ACTIVE_RING[phase.color]}` : ""}
                    ${state === "future" ? `${FUTURE_BG[phase.color]} text-gray-400` : ""}
                  `}
                >
                  {state === "complete" ? (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  ) : (
                    <span className="text-xs">{index + 1}</span>
                  )}
                </div>
                <span
                  className={`
                    mt-2 text-xs font-medium transition-all duration-300
                    ${state === "complete" ? "text-green-600" : ""}
                    ${state === "active" ? `${LABEL_COLOR[phase.color]} font-semibold` : ""}
                    ${state === "future" ? "text-gray-400" : ""}
                  `}
                >
                  {t(phase.key)}
                </span>
              </div>

              {!isLast && (
                <div className="flex-1 mx-3 relative top-[-12px]">
                  {index < currentIndex ? (
                    <div className="h-0.5 rounded bg-green-400 transition-all duration-300" />
                  ) : (
                    <div
                      className="h-0.5 rounded transition-all duration-300"
                      style={{ backgroundImage: "repeating-linear-gradient(90deg, #d1d5db 0, #d1d5db 6px, transparent 6px, transparent 12px)" }}
                    />
                  )}
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
