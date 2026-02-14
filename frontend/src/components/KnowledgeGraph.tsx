/* KnowledgeGraph — visual graph of validated knowledge claims. */
import { useTranslation } from "react-i18next";
import type { GraphData } from "../types";

interface KnowledgeGraphProps {
  data: GraphData;
}

const NODE_BORDER: Record<string, string> = {
  validated: "border-green-500",
  proposed: "border-blue-500",
  rejected: "border-red-400",
  qualified: "border-amber-500",
  user_contributed: "border-purple-500",
  gap: "border-gray-300",
};

const NODE_ICON: Record<string, { symbol: string; color: string }> = {
  validated: { symbol: "\u2713", color: "text-green-600" },
  rejected: { symbol: "\u2717", color: "text-red-500" },
  qualified: { symbol: "~", color: "text-amber-600" },
};

const EDGE_COLOR: Record<string, string> = {
  supports: "text-green-600",
  contradicts: "text-red-500",
  extends: "text-blue-600",
  supersedes: "text-amber-600",
  depends_on: "text-gray-500",
  merged_from: "text-purple-600",
};

export default function KnowledgeGraph({ data }: KnowledgeGraphProps) {
  const { t } = useTranslation();

  const nodesByRound = data.nodes.reduce((acc, node) => {
    const round = node.data.round_created || 0;
    if (!acc[round]) acc[round] = [];
    acc[round].push(node);
    return acc;
  }, {} as Record<number, typeof data.nodes>);

  const rounds = Object.keys(nodesByRound)
    .map(Number)
    .sort((a, b) => a - b);

  const findEdgesForNode = (nodeId: string) => {
    return data.edges.filter((e) => e.source === nodeId || e.target === nodeId);
  };

  return (
    <div className="w-full h-full bg-white border border-gray-200/80 rounded-xl shadow-md shadow-gray-200/40 overflow-auto">
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">{t("graph.title")}</h2>
        <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full font-medium">
          {t("graph.nodeCount", { count: data.nodes.length })}
        </span>
      </div>

      <div className="p-5 space-y-6">
        {rounds.map((round) => (
          <div key={round}>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              {t("graph.round", { round })}
            </h3>
            <div className="space-y-3">
              {nodesByRound[round].map((node) => {
                const edges = findEdgesForNode(node.id);
                const borderColor = NODE_BORDER[node.type as keyof typeof NODE_BORDER] || NODE_BORDER.proposed;
                const icon = NODE_ICON[node.type as keyof typeof NODE_ICON];
                const isRejected = node.type === "rejected";

                return (
                  <div
                    key={node.id}
                    className={`border-2 rounded-lg p-3 bg-white ${borderColor}`}
                  >
                    <div className="flex items-start justify-between mb-1.5">
                      <span className="text-xs font-mono text-gray-400">
                        {node.id.slice(0, 8)}
                      </span>
                      <div className="flex items-center gap-1.5">
                        {node.data.confidence && (
                          <span className="text-xs text-gray-500 font-medium">
                            {node.data.confidence}
                          </span>
                        )}
                        {icon && (
                          <span className={`text-sm font-bold ${icon.color}`}>
                            {icon.symbol}
                          </span>
                        )}
                      </div>
                    </div>

                    <p className={`text-sm leading-snug line-clamp-3 ${isRejected ? "text-gray-400 line-through" : "text-gray-800"}`}>
                      {node.data.claim_text}
                    </p>

                    {node.data.scores && (
                      <div className="flex gap-3 mt-2 text-xs text-gray-400">
                        {node.data.scores.novelty != null && (
                          <span>N: {node.data.scores.novelty.toFixed(1)}</span>
                        )}
                        {node.data.scores.significance != null && (
                          <span>S: {node.data.scores.significance.toFixed(1)}</span>
                        )}
                      </div>
                    )}

                    {node.data.qualification && (
                      <div className="text-xs mt-2 pt-2 border-t border-gray-100 text-gray-500">
                        {node.data.qualification}
                      </div>
                    )}

                    {edges.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-100 space-y-0.5">
                        {edges.map((edge, idx) => (
                          <div key={idx} className="flex items-center gap-1.5 text-xs">
                            <span className={`font-medium ${EDGE_COLOR[edge.type] || "text-gray-500"}`}>
                              {edge.type}
                            </span>
                            <span className="text-gray-400">
                              {edge.source === node.id
                                ? edge.target.slice(0, 8)
                                : edge.source.slice(0, 8)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {data.nodes.length === 0 && (
        <p className="text-gray-400 text-sm text-center py-8">
          {t("graph.empty")}
        </p>
      )}
    </div>
  );
}
