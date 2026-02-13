import { useState } from "react";
import type { Claim, ClaimVerdict, UserInput, VerdictType } from "../types";
import ClaimCard from "./ClaimCard";

interface VerdictPanelProps {
  claims: Claim[];
  onSubmit: (input: UserInput) => void;
}

export default function VerdictPanel({ claims, onSubmit }: VerdictPanelProps) {
  const [verdicts, setVerdicts] = useState<Map<number, ClaimVerdict>>(new Map());

  const updateVerdict = (
    claimIndex: number,
    field: keyof ClaimVerdict,
    value: unknown
  ) => {
    setVerdicts((prev) => {
      const updated = new Map(prev);
      const current = updated.get(claimIndex) || {
        claim_index: claimIndex,
        verdict: "accept" as VerdictType,
      };
      updated.set(claimIndex, { ...current, [field]: value });
      return updated;
    });
  };

  const setVerdictType = (claimIndex: number, verdict: VerdictType) => {
    updateVerdict(claimIndex, "verdict", verdict);
  };

  const handleSubmit = () => {
    const verdictList: ClaimVerdict[] = [];
    for (let i = 0; i < claims.length; i++) {
      const v = verdicts.get(i);
      if (v) {
        verdictList.push(v);
      } else {
        verdictList.push({
          claim_index: i,
          verdict: "accept",
        });
      }
    }
    onSubmit({
      type: "verdicts",
      verdicts: verdictList,
    });
  };

  return (
    <div className="space-y-6">
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
        <h2 className="text-xl font-semibold text-white mb-2">
          Phase 4: Render Verdicts
        </h2>
        <p className="text-gray-400 text-sm">
          Decide the fate of each claim. Accept, reject, qualify (true only if...), or
          merge with another claim.
        </p>
      </div>

      {claims.map((claim, i) => {
        const currentVerdict = verdicts.get(i)?.verdict || "accept";

        return (
          <div key={i} className="space-y-3">
            <ClaimCard claim={claim} index={i} />
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 space-y-3">
              <div className="grid grid-cols-4 gap-2">
                <button
                  onClick={() => setVerdictType(i, "accept")}
                  className={`py-2 px-3 rounded font-medium text-sm transition-colors ${
                    currentVerdict === "accept"
                      ? "bg-green-600 text-white"
                      : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                  }`}
                >
                  Accept
                </button>
                <button
                  onClick={() => setVerdictType(i, "reject")}
                  className={`py-2 px-3 rounded font-medium text-sm transition-colors ${
                    currentVerdict === "reject"
                      ? "bg-red-600 text-white"
                      : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                  }`}
                >
                  Reject
                </button>
                <button
                  onClick={() => setVerdictType(i, "qualify")}
                  className={`py-2 px-3 rounded font-medium text-sm transition-colors ${
                    currentVerdict === "qualify"
                      ? "bg-yellow-600 text-white"
                      : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                  }`}
                >
                  Qualify
                </button>
                <button
                  onClick={() => setVerdictType(i, "merge")}
                  className={`py-2 px-3 rounded font-medium text-sm transition-colors ${
                    currentVerdict === "merge"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                  }`}
                >
                  Merge
                </button>
              </div>

              {currentVerdict === "reject" && (
                <div>
                  <label className="block text-sm text-gray-400 mb-1">
                    Rejection reason
                  </label>
                  <input
                    type="text"
                    value={verdicts.get(i)?.rejection_reason || ""}
                    onChange={(e) =>
                      updateVerdict(i, "rejection_reason", e.target.value)
                    }
                    placeholder="Why is this claim invalid..."
                    className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
              )}

              {currentVerdict === "qualify" && (
                <div>
                  <label className="block text-sm text-gray-400 mb-1">
                    Qualification (true only if...)
                  </label>
                  <input
                    type="text"
                    value={verdicts.get(i)?.qualification || ""}
                    onChange={(e) =>
                      updateVerdict(i, "qualification", e.target.value)
                    }
                    placeholder="This claim is true only if..."
                    className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-yellow-500"
                  />
                </div>
              )}

              {currentVerdict === "merge" && (
                <div>
                  <label className="block text-sm text-gray-400 mb-1">
                    Merge with claim
                  </label>
                  <select
                    value={verdicts.get(i)?.merge_with_claim_id || ""}
                    onChange={(e) =>
                      updateVerdict(i, "merge_with_claim_id", e.target.value)
                    }
                    className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Select a claim...</option>
                    {claims.map((c, origIdx) =>
                      origIdx !== i ? (
                        <option key={origIdx} value={c.claim_id || `claim-${origIdx}`}>
                          #{origIdx + 1}: {c.claim_text.slice(0, 60)}...
                        </option>
                      ) : null
                    )}
                  </select>
                </div>
              )}
            </div>
          </div>
        );
      })}

      <button
        onClick={handleSubmit}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg transition-colors"
      >
        Submit Verdicts
      </button>
    </div>
  );
}
