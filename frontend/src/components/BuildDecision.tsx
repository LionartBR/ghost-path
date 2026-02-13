import { useState } from "react";
import type { BuildReviewData, UserInput, BuildDecision as BuildDecisionType } from "../types";
import UserInsightForm from "./UserInsightForm";

interface BuildDecisionProps {
  data: BuildReviewData;
  onSubmit: (input: UserInput) => void;
}

export default function BuildDecision({ data, onSubmit }: BuildDecisionProps) {
  const [showInsightForm, setShowInsightForm] = useState(false);
  const [selectedClaimId, setSelectedClaimId] = useState<string>("");

  const handleDecision = (decision: BuildDecisionType) => {
    if (decision === "deep_dive") {
      if (!selectedClaimId) {
        alert("Please select a claim to deep-dive on");
        return;
      }
      onSubmit({
        type: "build_decision",
        decision,
        deep_dive_claim_id: selectedClaimId,
      });
    } else if (decision === "add_insight") {
      setShowInsightForm(true);
    } else {
      onSubmit({
        type: "build_decision",
        decision,
      });
    }
  };

  const handleInsightSubmit = (insight: string, urls: string[]) => {
    onSubmit({
      type: "build_decision",
      decision: "add_insight",
      user_insight: insight,
      user_evidence_urls: urls,
    });
    setShowInsightForm(false);
  };

  if (showInsightForm) {
    return (
      <UserInsightForm
        onSubmit={handleInsightSubmit}
        onCancel={() => setShowInsightForm(false)}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
        <h2 className="text-xl font-semibold text-white mb-2">
          Phase 5: Build Decision (Round {data.round})
        </h2>
        <p className="text-gray-400 text-sm">
          Review the knowledge graph, gaps, and negative knowledge. Decide whether to
          continue exploring, deep-dive on a claim, resolve the session, or add your own
          insight.
        </p>
      </div>

      {data.gaps.length > 0 && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-3">
            Knowledge Gaps Identified
          </h3>
          <ul className="space-y-2">
            {data.gaps.map((gap, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-yellow-500 text-sm mt-0.5">▲</span>
                <span className="text-gray-300 text-sm">{gap}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {data.negative_knowledge.length > 0 && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-3">
            Negative Knowledge (Rejected Claims)
          </h3>
          <div className="space-y-3">
            {data.negative_knowledge.map((nk, i) => (
              <div key={i} className="bg-gray-900 border border-gray-700 rounded p-3">
                <p className="text-gray-300 text-sm mb-1">{nk.claim_text}</p>
                <p className="text-red-400 text-xs">
                  Rejected (Round {nk.round}): {nk.rejection_reason}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-white mb-3">
          Graph Summary
        </h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Nodes:</span>
            <span className="text-white ml-2 font-mono">
              {data.graph.nodes.length}
            </span>
          </div>
          <div>
            <span className="text-gray-400">Edges:</span>
            <span className="text-white ml-2 font-mono">
              {data.graph.edges.length}
            </span>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => handleDecision("continue")}
            disabled={data.max_rounds_reached}
            className={`py-3 px-4 rounded-lg font-medium transition-colors ${
              data.max_rounds_reached
                ? "bg-gray-700 text-gray-500 cursor-not-allowed"
                : "bg-green-600 hover:bg-green-700 text-white"
            }`}
          >
            Continue Next Round
          </button>
          <button
            onClick={() => handleDecision("resolve")}
            className="bg-blue-600 hover:bg-blue-700 text-white py-3 px-4 rounded-lg font-medium transition-colors"
          >
            Resolve (Crystallize)
          </button>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-lg p-3">
          <label className="block text-sm text-gray-400 mb-2">
            Deep-dive on a specific claim
          </label>
          <div className="flex gap-2">
            <select
              value={selectedClaimId}
              onChange={(e) => setSelectedClaimId(e.target.value)}
              disabled={data.max_rounds_reached}
              className="flex-1 bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="">Select a claim...</option>
              {data.graph.nodes.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.data.claim_text.slice(0, 60)}...
                </option>
              ))}
            </select>
            <button
              onClick={() => handleDecision("deep_dive")}
              disabled={data.max_rounds_reached || !selectedClaimId}
              className="bg-purple-600 hover:bg-purple-700 text-white py-2 px-4 rounded font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Deep-dive
            </button>
          </div>
        </div>

        <button
          onClick={() => handleDecision("add_insight")}
          className="w-full bg-yellow-600 hover:bg-yellow-700 text-white py-3 px-4 rounded-lg font-medium transition-colors"
        >
          Add Your Own Insight
        </button>
      </div>

      {data.max_rounds_reached && (
        <div className="bg-red-900 border border-red-700 rounded-lg p-4">
          <p className="text-red-200 text-sm">
            Maximum rounds reached. You can only Resolve or Add Your Own Insight.
          </p>
        </div>
      )}
    </div>
  );
}
