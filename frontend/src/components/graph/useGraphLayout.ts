/* useGraphLayout — transforms GraphNode[] + GraphEdge[] into React Flow nodes with dagre positions.

Invariants:
    - Dagre computes center positions; React Flow uses top-left — offset by half node size
    - Layout recomputes only when nodes/edges change (useMemo)

Design Decisions:
    - TB (top-to-bottom) rankdir aligns with round progression (ADR: matches mental model)
    - Fixed node dimensions for uniform dagre spacing
*/

import { useMemo } from "react";
import dagre from "dagre";
import type { Node, Edge } from "@xyflow/react";
import type { GraphNode, GraphEdge } from "../../types";

const NODE_WIDTH = 280;
const NODE_HEIGHT = 120;

export function useGraphLayout(
  graphNodes: GraphNode[],
  graphEdges: GraphEdge[],
): { nodes: Node[]; edges: Edge[] } {
  return useMemo(() => {
    if (graphNodes.length === 0) return { nodes: [], edges: [] };

    const g = new dagre.graphlib.Graph();
    g.setDefaultEdgeLabel(() => ({}));
    g.setGraph({ rankdir: "TB", nodesep: 60, ranksep: 100 });

    for (const node of graphNodes) {
      g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
    }
    for (const edge of graphEdges) {
      g.setEdge(edge.source, edge.target);
    }

    dagre.layout(g);

    const nodes: Node[] = graphNodes.map((gn) => {
      const pos = g.node(gn.id);
      return {
        id: gn.id,
        type: "claim",
        position: {
          x: pos.x - NODE_WIDTH / 2,
          y: pos.y - NODE_HEIGHT / 2,
        },
        data: { ...gn.data, nodeType: gn.type },
      };
    });

    const edges: Edge[] = graphEdges.map((ge) => ({
      id: ge.id,
      source: ge.source,
      target: ge.target,
      type: "default",
      data: { edgeType: ge.type },
    }));

    return { nodes, edges };
  }, [graphNodes, graphEdges]);
}
