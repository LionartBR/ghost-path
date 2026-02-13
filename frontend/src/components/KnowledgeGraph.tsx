/* KnowledgeGraph — visual graph of validated knowledge claims. */
import type { GraphData } from "../types";

interface KnowledgeGraphProps {
  data: GraphData;
}

const NODE_COLORS = {
  validated: "bg-green-600 border-green-400",
  proposed: "bg-blue-600 border-blue-400",
  rejected: "bg-red-600 border-red-400",
  qualified: "bg-yellow-600 border-yellow-400",
  user_contributed: "bg-purple-600 border-purple-400",
  gap: "bg-gray-600 border-gray-400",
};

export default function KnowledgeGraph({ data }: KnowledgeGraphProps) {
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
    <div className="w-full h-full bg-gray-800 rounded-lg p-6 overflow-auto">
      <h2 className="text-xl font-bold mb-4 text-white">Knowledge Graph</h2>
      <div className="space-y-8">
        {rounds.map((round) => (
          <div key={round} className="border-l-2 border-gray-600 pl-4">
            <h3 className="text-lg font-semibold mb-3 text-gray-300">
              Round {round}
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {nodesByRound[round].map((node) => {
                const edges = findEdgesForNode(node.id);
                const nodeColor = NODE_COLORS[node.type as keyof typeof NODE_COLORS] || NODE_COLORS.proposed;
                return (
                  <div
                    key={node.id}
                    className={`border-2 rounded-lg p-4 ${nodeColor}`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <span className="text-xs font-mono bg-black bg-opacity-30 px-2 py-1 rounded">
                        {node.id.slice(0, 8)}
                      </span>
                      {node.data.confidence && (
                        <span className="text-xs font-bold bg-white text-gray-900 px-2 py-1 rounded">
                          {node.data.confidence}
                        </span>
                      )}
                    </div>
                    <p className="text-sm mb-2 line-clamp-3">
                      {node.data.claim_text}
                    </p>
                    {node.data.scores && (
                      <div className="text-xs space-y-1 opacity-80">
                        {node.data.scores.novelty && (
                          <div>Novel: {node.data.scores.novelty.toFixed(1)}</div>
                        )}
                        {node.data.scores.significance && (
                          <div>Significance: {node.data.scores.significance.toFixed(1)}</div>
                        )}
                        {node.data.scores.groundedness && (
                          <div>Groundedness: {node.data.scores.groundedness.toFixed(1)}</div>
                        )}
                      </div>
                    )}
                    {node.data.qualification && (
                      <div className="text-xs mt-2 pt-2 border-t border-white border-opacity-20 opacity-70">
                        {node.data.qualification}
                      </div>
                    )}
                    {edges.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-white border-opacity-20">
                        <p className="text-xs font-semibold mb-1">
                          Connections:
                        </p>
                        {edges.map((edge, idx) => (
                          <div key={idx} className="text-xs opacity-70">
                            {edge.type}:{" "}
                            {edge.source === node.id
                              ? edge.target.slice(0, 8)
                              : edge.source.slice(0, 8)}
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
        <p className="text-gray-400 text-center py-8">
          No nodes in the graph yet.
        </p>
      )}
    </div>
  );
}
