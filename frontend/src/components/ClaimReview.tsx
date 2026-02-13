import { useState } from "react";
import type { Claim, ClaimFeedback, UserInput } from "../types";
import ClaimCard from "./ClaimCard";

interface ClaimReviewProps {
  claims: Claim[];
  onSubmit: (input: UserInput) => void;
}

export default function ClaimReview({ claims, onSubmit }: ClaimReviewProps) {
  const [feedback, setFeedback] = useState<Map<number, ClaimFeedback>>(
    new Map()
  );

  const updateFeedback = (
    claimIndex: number,
    field: keyof ClaimFeedback,
    value: unknown
  ) => {
    setFeedback((prev) => {
      const updated = new Map(prev);
      const current = updated.get(claimIndex) || {
        claim_index: claimIndex,
        evidence_valid: false,
      };
      updated.set(claimIndex, { ...current, [field]: value });
      return updated;
    });
  };

  const handleSubmit = () => {
    const claim_feedback: ClaimFeedback[] = [];
    for (let i = 0; i < claims.length; i++) {
      const fb = feedback.get(i);
      if (fb) {
        claim_feedback.push(fb);
      } else {
        claim_feedback.push({
          claim_index: i,
          evidence_valid: false,
        });
      }
    }
    onSubmit({
      type: "claims_review",
      claim_feedback,
    });
  };

  return (
    <div className="space-y-6">
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
        <h2 className="text-xl font-semibold text-white mb-2">
          Phase 3: Validate Evidence
        </h2>
        <p className="text-gray-400 text-sm">
          Review each claim's evidence quality. Mark whether the evidence is valid,
          provide counter-examples if you know of any, note missing factors, or suggest
          additional evidence sources.
        </p>
      </div>

      {claims.map((claim, i) => (
        <div key={i} className="space-y-3">
          <ClaimCard claim={claim} index={i} />
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 space-y-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={feedback.get(i)?.evidence_valid || false}
                onChange={(e) =>
                  updateFeedback(i, "evidence_valid", e.target.checked)
                }
                className="w-4 h-4 bg-gray-700 border-gray-600 rounded text-blue-500 focus:ring-blue-500"
              />
              <span className="text-white text-sm font-medium">
                Evidence is valid and supports the claim
              </span>
            </label>

            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Counter-example (if any)
              </label>
              <input
                type="text"
                value={feedback.get(i)?.counter_example || ""}
                onChange={(e) =>
                  updateFeedback(i, "counter_example", e.target.value)
                }
                placeholder="Describe a case where this claim doesn't hold..."
                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Missing factors in synthesis
              </label>
              <input
                type="text"
                value={feedback.get(i)?.synthesis_ignores || ""}
                onChange={(e) =>
                  updateFeedback(i, "synthesis_ignores", e.target.value)
                }
                placeholder="What important factors were ignored..."
                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Additional evidence (URLs or references)
              </label>
              <input
                type="text"
                value={feedback.get(i)?.additional_evidence || ""}
                onChange={(e) =>
                  updateFeedback(i, "additional_evidence", e.target.value)
                }
                placeholder="Suggest additional sources..."
                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>
      ))}

      <button
        onClick={handleSubmit}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg transition-colors"
      >
        Submit Evidence Review
      </button>
    </div>
  );
}
