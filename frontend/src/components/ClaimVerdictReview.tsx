/* ClaimVerdictReview — unified claim display + verdict buttons (replaces separate ClaimReview + VerdictPanel). */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { Claim, ClaimVerdict, UserInput, VerdictType } from "../types";
import ClaimCard from "./ClaimCard";

interface ClaimVerdictReviewProps {
  claims: Claim[];
  onSubmit: (input: UserInput) => void;
}

const VERDICT_STYLES: Record<VerdictType, { active: string; inactive: string }> = {
  accept: {
    active: "bg-blue-600 text-white",
    inactive: "bg-white border border-gray-200 text-gray-600 hover:bg-blue-50",
  },
  reject: {
    active: "bg-blue-400 text-white",
    inactive: "bg-white border border-gray-200 text-gray-600 hover:bg-blue-50",
  },
  qualify: {
    active: "bg-blue-500 text-white",
    inactive: "bg-white border border-gray-200 text-gray-600 hover:bg-blue-50",
  },
  merge: {
    active: "bg-blue-500 text-white",
    inactive: "bg-white border border-gray-200 text-gray-600 hover:bg-blue-50",
  },
};

const VERDICT_KEYS: Record<VerdictType, string> = {
  accept: "verdicts.accept",
  reject: "verdicts.reject",
  qualify: "verdicts.qualify",
  merge: "verdicts.merge",
};

export default function ClaimVerdictReview({ claims, onSubmit }: ClaimVerdictReviewProps) {
  const { t } = useTranslation();
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
    <div className="space-y-5">
      <div className="bg-white border border-gray-200/80 rounded-xl shadow-md shadow-gray-200/40 p-5">
        <h2 className="text-base font-semibold text-gray-900 mb-1">
          {t("verdicts.title")}
        </h2>
        <p className="text-gray-500 text-sm">
          {t("verdicts.unifiedDescription")}
        </p>
      </div>

      {claims.map((claim, i) => {
        const currentVerdict = verdicts.get(i)?.verdict || "accept";

        return (
          <div key={i} className="space-y-3">
            <ClaimCard claim={claim} index={i} compact />
            <div className="bg-white border border-gray-200/80 rounded-xl shadow-md shadow-gray-200/40 p-4 space-y-3">
              <div className="grid grid-cols-4 gap-2">
                {(["accept", "reject", "qualify", "merge"] as VerdictType[]).map((v) => (
                  <button
                    key={v}
                    onClick={() => setVerdictType(i, v)}
                    className={`py-2 px-3 rounded-md font-medium text-sm transition-colors ${
                      currentVerdict === v
                        ? VERDICT_STYLES[v].active
                        : VERDICT_STYLES[v].inactive
                    }`}
                  >
                    {t(VERDICT_KEYS[v])}
                  </button>
                ))}
              </div>

              {currentVerdict === "reject" && (
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    {t("verdicts.rejectionReason")}
                  </label>
                  <input
                    type="text"
                    value={verdicts.get(i)?.rejection_reason || ""}
                    onChange={(e) =>
                      updateVerdict(i, "rejection_reason", e.target.value)
                    }
                    className="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-400"
                  />
                </div>
              )}

              {currentVerdict === "qualify" && (
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    {t("verdicts.qualification")}
                  </label>
                  <input
                    type="text"
                    value={verdicts.get(i)?.qualification || ""}
                    onChange={(e) =>
                      updateVerdict(i, "qualification", e.target.value)
                    }
                    className="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-400"
                  />
                </div>
              )}

              {currentVerdict === "merge" && (
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    {t("verdicts.mergeWith")}
                  </label>
                  <select
                    value={verdicts.get(i)?.merge_with_claim_id || ""}
                    onChange={(e) =>
                      updateVerdict(i, "merge_with_claim_id", e.target.value)
                    }
                    className="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">{t("verdicts.selectClaim")}</option>
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
        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm py-3 px-6 rounded-lg shadow-md shadow-blue-200/50 hover:shadow-lg hover:shadow-blue-300/50 transition-all"
      >
        {t("verdicts.submit")}
      </button>
    </div>
  );
}
