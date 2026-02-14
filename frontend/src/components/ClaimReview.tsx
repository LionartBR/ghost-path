import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { Claim, ClaimFeedback, UserInput } from "../types";
import ClaimCard from "./ClaimCard";

interface ClaimReviewProps {
  claims: Claim[];
  onSubmit: (input: UserInput) => void;
}

export default function ClaimReview({ claims, onSubmit }: ClaimReviewProps) {
  const { t } = useTranslation();
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
    <div className="space-y-5">
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-5">
        <h2 className="text-base font-semibold text-gray-900 mb-1">
          {t("claims.title")}
        </h2>
        <p className="text-gray-500 text-sm">
          {t("claims.description")}
        </p>
      </div>

      {claims.map((claim, i) => (
        <div key={i} className="space-y-3">
          <ClaimCard claim={claim} index={i} />
          <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-5 space-y-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={feedback.get(i)?.evidence_valid || false}
                onChange={(e) =>
                  updateFeedback(i, "evidence_valid", e.target.checked)
                }
                className="w-4 h-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span className="text-gray-900 text-sm font-medium">
                {t("claims.evidenceValid")}
              </span>
            </label>

            <div>
              <label className="block text-xs text-gray-500 mb-1">
                {t("claims.counterExample")}
              </label>
              <input
                type="text"
                value={feedback.get(i)?.counter_example || ""}
                onChange={(e) =>
                  updateFeedback(i, "counter_example", e.target.value)
                }
                className="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent placeholder-gray-400"
              />
            </div>

            <div>
              <label className="block text-xs text-gray-500 mb-1">
                {t("claims.missingFactors")}
              </label>
              <input
                type="text"
                value={feedback.get(i)?.synthesis_ignores || ""}
                onChange={(e) =>
                  updateFeedback(i, "synthesis_ignores", e.target.value)
                }
                className="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent placeholder-gray-400"
              />
            </div>

            <div>
              <label className="block text-xs text-gray-500 mb-1">
                {t("claims.additionalEvidence")}
              </label>
              <input
                type="text"
                value={feedback.get(i)?.additional_evidence || ""}
                onChange={(e) =>
                  updateFeedback(i, "additional_evidence", e.target.value)
                }
                className="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent placeholder-gray-400"
              />
            </div>
          </div>
        </div>
      ))}

      <button
        onClick={handleSubmit}
        className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm py-2.5 px-6 rounded-md transition-colors"
      >
        {t("claims.submit")}
      </button>
    </div>
  );
}
