import React from "react";
import type { Phase } from "../types";

interface PhaseTimelineProps {
  currentPhase: Phase | null;
}

const PHASES: { name: Phase; label: string; color: string }[] = [
  { name: "decompose", label: "Decompose", color: "purple" },
  { name: "explore", label: "Explore", color: "blue" },
  { name: "synthesize", label: "Synthesize", color: "green" },
  { name: "validate", label: "Validate", color: "orange" },
  { name: "build", label: "Build", color: "red" },
  { name: "crystallize", label: "Crystallize", color: "white" },
];

/** Static color map — CSS var() interpolation doesn't work with template strings. */
const PHASE_SHADOW_COLORS: Record<string, string> = {
  purple: "#a855f7",
  blue: "#3b82f6",
  green: "#22c55e",
  orange: "#f97316",
  red: "#ef4444",
  white: "#ffffff",
};

const getPhaseIndex = (phase: Phase | null): number => {
  if (!phase) return -1;
  return PHASES.findIndex((p) => p.name === phase);
};

const getPhaseColorClasses = (
  color: string,
  state: "active" | "complete" | "future"
): string => {
  if (state === "future") return "bg-gray-700 text-gray-500";
  if (state === "complete") return "bg-green-600 text-white";

  const colorMap: Record<string, string> = {
    purple: "bg-purple-500 text-white",
    blue: "bg-blue-500 text-white",
    green: "bg-green-500 text-white",
    orange: "bg-orange-500 text-white",
    red: "bg-red-500 text-white",
    white: "bg-white text-gray-900",
  };
  return colorMap[color] || "bg-gray-500 text-white";
};

export const PhaseTimeline: React.FC<PhaseTimelineProps> = ({ currentPhase }) => {
  const currentIndex = getPhaseIndex(currentPhase);

  return (
    <div className="w-full py-6 px-4 bg-gray-800 rounded-lg">
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
                    w-12 h-12 rounded-full flex items-center justify-center
                    font-bold text-sm transition-all duration-300
                    ${getPhaseColorClasses(phase.color, state)}
                    ${state === "active" ? "ring-4 ring-offset-2 ring-offset-gray-900" : ""}
                  `}
                  style={
                    state === "active"
                      ? { boxShadow: `0 0 0 4px ${PHASE_SHADOW_COLORS[phase.color] || "#3b82f6"}` }
                      : undefined
                  }
                >
                  {state === "complete" ? (
                    <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  ) : (
                    <span>{index + 1}</span>
                  )}
                </div>
                <div
                  className={`
                    mt-2 text-xs font-medium transition-opacity duration-300
                    ${state === "future" ? "opacity-50" : "opacity-100"}
                  `}
                >
                  {phase.label}
                </div>
              </div>

              {!isLast && (
                <div className="flex-1 h-1 mx-2 relative top-[-20px]">
                  <div
                    className={`
                      h-full rounded transition-all duration-300
                      ${index < currentIndex ? "bg-green-600" : "bg-gray-700"}
                    `}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
