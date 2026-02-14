/* FlowGraph — interactive React Flow DAG for knowledge claims.

Invariants:
    - nodeTypes must be stable (useMemo) to avoid React Flow re-mounting nodes
    - ReactFlowProvider wraps the inner component (required for useReactFlow hook)
    - fitView triggers on node count change for auto-framing

Design Decisions:
    - Edge styles encode relationship semantics (ADR: color/dash = instant visual parsing)
    - MiniMap uses nodeColor callback matching status colors for consistency
    - Background dots + Controls for standard graph UX affordances
*/

import { useCallback, useEffect, useMemo } from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  useReactFlow,
  type EdgeProps,
  BaseEdge,
  getStraightPath,
} from "@xyflow/react";
import { useTranslation } from "react-i18next";
import ClaimNode from "./ClaimNode";
import { useGraphLayout } from "./useGraphLayout";
import type { GraphData } from "../../types";

const EDGE_STYLES: Record<string, { stroke: string; strokeDasharray?: string; strokeWidth: number }> = {
  supports:    { stroke: "#16a34a", strokeWidth: 2 },
  contradicts: { stroke: "#ef4444", strokeDasharray: "6 3", strokeWidth: 2 },
  extends:     { stroke: "#3b82f6", strokeWidth: 2 },
  supersedes:  { stroke: "#d97706", strokeWidth: 3 },
  depends_on:  { stroke: "#9ca3af", strokeDasharray: "3 3", strokeWidth: 1.5 },
  merged_from: { stroke: "#9333ea", strokeWidth: 2 },
};

const DEFAULT_EDGE_STYLE = { stroke: "#9ca3af", strokeWidth: 1.5 };

const MINIMAP_COLORS: Record<string, string> = {
  validated: "#16a34a",
  proposed: "#3b82f6",
  rejected: "#ef4444",
  qualified: "#d97706",
  superseded: "#9ca3af",
  user_contributed: "#9333ea",
  gap: "#d1d5db",
};

function LabeledEdge({ id, sourceX, sourceY, targetX, targetY, data }: EdgeProps) {
  const edgeType = (data as Record<string, unknown>)?.edgeType as string | undefined;
  const style = EDGE_STYLES[edgeType ?? ""] ?? DEFAULT_EDGE_STYLE;

  const [path, labelX, labelY] = getStraightPath({
    sourceX, sourceY, targetX, targetY,
  });

  return (
    <>
      <BaseEdge id={id} path={path} style={style} />
      {edgeType && (
        <text
          x={labelX}
          y={labelY - 8}
          textAnchor="middle"
          className="text-[9px] fill-gray-500 pointer-events-none select-none"
        >
          {edgeType}
        </text>
      )}
    </>
  );
}

interface FlowGraphInnerProps {
  data: GraphData;
}

function FlowGraphInner({ data }: FlowGraphInnerProps) {
  const { t } = useTranslation();
  const { fitView } = useReactFlow();

  const nodeTypes = useMemo(() => ({ claim: ClaimNode }), []);
  const edgeTypes = useMemo(() => ({ default: LabeledEdge }), []);

  const { nodes, edges } = useGraphLayout(data.nodes, data.edges);

  const nodeCount = nodes.length;
  useEffect(() => {
    if (nodeCount > 0) {
      const timer = setTimeout(() => fitView({ padding: 0.2, duration: 300 }), 50);
      return () => clearTimeout(timer);
    }
  }, [nodeCount, fitView]);

  const miniMapNodeColor = useCallback((node: { data?: Record<string, unknown> }) => {
    const nodeType = (node.data?.nodeType as string) ?? "proposed";
    return MINIMAP_COLORS[nodeType] ?? "#3b82f6";
  }, []);

  if (nodes.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <p className="text-gray-400 text-sm">{t("graph.empty")}</p>
      </div>
    );
  }

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      minZoom={0.3}
      maxZoom={1.5}
      proOptions={{ hideAttribution: true }}
      nodesDraggable={false}
      nodesConnectable={false}
    >
      <Background gap={16} size={1} />
      <Controls position="bottom-right" showInteractive={false} />
      <MiniMap
        position="bottom-left"
        nodeColor={miniMapNodeColor}
        maskColor="rgba(0,0,0,0.08)"
        pannable
        zoomable
      />
    </ReactFlow>
  );
}

interface FlowGraphProps {
  data: GraphData;
}

export default function FlowGraph({ data }: FlowGraphProps) {
  return (
    <ReactFlowProvider>
      <FlowGraphInner data={data} />
    </ReactFlowProvider>
  );
}
