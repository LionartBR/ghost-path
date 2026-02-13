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
    <div className="space-y-5">
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-5">
        <h2 className="text-base font-semibold text-gray-900 mb-1">
          Phase 5: Build Decision (Round {data.round})
        </h2>
        <p className="text-gray-500 text-sm">
          Review the knowledge graph, gaps, and negative knowledge. Decide whether to
          continue exploring, deep-dive on a claim, resolve the session, or add your own
          insight.
        </p>
      </div>

      {data.gaps.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">
            Knowledge Gaps Identified
          </h3>
          <ul className="space-y-2">
            {data.gaps.map((gap, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-amber-500 text-sm mt-0.5">&#9650;</span>
                <span className="text-gray-600 text-sm">{gap}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {data.negative_knowledge.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">
            Negative Knowledge (Rejected Claims)
          </h3>
          <div className="space-y-2">
            {data.negative_knowledge.map((nk, i) => (
              <div key={i} className="bg-gray-50 border border-gray-100 rounded-md p-3">
                <p className="text-gray-700 text-sm mb-1">{nk.claim_text}</p>
                <p className="text-red-500 text-xs">
                  Rejected (Round {nk.round}): {nk.rejection_reason}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">
          Graph Summary
        </h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Nodes:</span>
            <span className="text-gray-900 ml-2 font-mono font-semibold">
              {data.graph.nodes.length}
            </span>
          </div>
          <div>
            <span className="text-gray-500">Edges:</span>
            <span className="text-gray-900 ml-2 font-mono font-semibold">
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
            className={`py-2.5 px-4 rounded-md font-medium text-sm transition-colors ${
              data.max_rounds_reached
                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                : "bg-green-600 hover:bg-green-700 text-white"
            }`}
          >
            Continue Next Round
          </button>
          <button
            onClick={() => handleDecision("resolve")}
            className="bg-indigo-600 hover:bg-indigo-700 text-white py-2.5 px-4 rounded-md font-medium text-sm transition-colors"
          >
            Resolve (Crystallize)
          </button>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
          <label className="block text-xs text-gray-500 mb-2">
            Deep-dive on a specific claim
          </label>
          <div className="flex gap-2">
            <select
              value={selectedClaimId}
              onChange={(e) => setSelectedClaimId(e.target.value)}
              disabled={data.max_rounds_reached}
              className="flex-1 bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
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
              className="bg-purple-600 hover:bg-purple-700 text-white py-2 px-4 rounded-md font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Deep-dive
            </button>
          </div>
        </div>

        <button
          onClick={() => handleDecision("add_insight")}
          className="w-full bg-amber-500 hover:bg-amber-600 text-white py-2.5 px-4 rounded-md font-medium text-sm transition-colors"
        >
          Add Your Own Insight
        </button>
      </div>

      {data.max_rounds_reached && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-700 text-sm">
            Maximum rounds reached. You can only Resolve or Add Your Own Insight.
          </p>
        </div>
      )}
    </div>
  );
}
