/* ClaimNode — custom React Flow node for knowledge claims.

Invariants:
    - Handle positions: top=target, bottom=source (TB layout)
    - Status determines visual: border color, icon, text styling

Design Decisions:
    - memo() prevents re-render on pan/zoom (ADR: React Flow renders all visible nodes)
    - Compact 280px card fits sidebar and full-screen layouts
*/

import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import type { NodeProps } from "@xyflow/react";
import { useTranslation } from "react-i18next";

interface ClaimNodeData {
  nodeType: string;
  claim_text: string;
  confidence?: string;
  scores: { novelty: number | null; significance: number | null };
  evidence_count: number;
  [key: string]: unknown;
}

const STATUS_CONFIG: Record<string, {
  border: string;
  icon: string;
  iconColor: string;
  textClass: string;
  bgClass: string;
}> = {
  validated: {
    border: "border-blue-600",
    icon: "\u2713",
    iconColor: "text-blue-700",
    textClass: "text-gray-800",
    bgClass: "bg-blue-50/50",
  },
  proposed: {
    border: "border-blue-500",
    icon: "\u25CB",
    iconColor: "text-blue-500",
    textClass: "text-gray-800",
    bgClass: "bg-blue-50/30",
  },
  rejected: {
    border: "border-blue-300",
    icon: "\u2717",
    iconColor: "text-blue-400",
    textClass: "text-gray-400 line-through",
    bgClass: "bg-blue-50/20",
  },
  qualified: {
    border: "border-blue-400",
    icon: "~",
    iconColor: "text-blue-500",
    textClass: "text-gray-800",
    bgClass: "bg-blue-50/30",
  },
  superseded: {
    border: "border-gray-300",
    icon: "\u2014",
    iconColor: "text-gray-400",
    textClass: "text-gray-400",
    bgClass: "bg-gray-50/50 opacity-70",
  },
  user_contributed: {
    border: "border-blue-500",
    icon: "\u2605",
    iconColor: "text-blue-600",
    textClass: "text-gray-800",
    bgClass: "bg-blue-50/30",
  },
  gap: {
    border: "border-gray-300 border-dashed",
    icon: "\u25B3",
    iconColor: "text-gray-400",
    textClass: "text-gray-500",
    bgClass: "bg-gray-50/50",
  },
};

const DEFAULT_CONFIG = STATUS_CONFIG.proposed;

const CONFIDENCE_BADGE: Record<string, string> = {
  speculative: "bg-blue-50 text-blue-400",
  emerging: "bg-blue-100 text-blue-600",
  grounded: "bg-blue-100 text-blue-700",
};

const CONFIDENCE_KEY: Record<string, string> = {
  speculative: "claims.confidence.speculative",
  emerging: "claims.confidence.emerging",
  grounded: "claims.confidence.grounded",
};

function ClaimNodeInner({ data }: NodeProps) {
  const { t } = useTranslation();
  const d = data as unknown as ClaimNodeData;
  const config = STATUS_CONFIG[d.nodeType] ?? DEFAULT_CONFIG;

  return (
    <div
      className={`w-[280px] border-2 rounded-lg shadow-sm ${config.border} ${config.bgClass}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-400 !w-2 !h-2" />

      {/* Header */}
      <div className="flex items-center justify-between px-3 pt-2.5 pb-1">
        <div className="flex items-center gap-1.5">
          <span className={`text-sm font-bold ${config.iconColor}`}>{config.icon}</span>
          <span className="text-xs font-mono text-gray-400">
            {(d as Record<string, unknown>).claim_id
              ? String((d as Record<string, unknown>).claim_id).slice(0, 8)
              : ""}
          </span>
        </div>
        {d.confidence && (
          <span
            className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${CONFIDENCE_BADGE[d.confidence] ?? "bg-gray-100 text-gray-500"}`}
          >
            {t(CONFIDENCE_KEY[d.confidence] || d.confidence)}
          </span>
        )}
      </div>

      {/* Body */}
      <div className="px-3 pb-1.5">
        <p className={`text-xs leading-relaxed line-clamp-2 ${config.textClass}`} title={d.claim_text}>
          {d.claim_text}
        </p>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-3 pb-2.5 text-[10px] text-gray-400">
        <div className="flex gap-2">
          {d.scores?.novelty != null && <span>N:{d.scores.novelty.toFixed(1)}</span>}
          {d.scores?.significance != null && <span>S:{d.scores.significance.toFixed(1)}</span>}
        </div>
        {d.evidence_count > 0 && (
          <span>{d.evidence_count} ev.</span>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-gray-400 !w-2 !h-2" />
    </div>
  );
}

const ClaimNode = memo(ClaimNodeInner);
export default ClaimNode;
