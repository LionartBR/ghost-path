import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { BuildReviewData, UserInput, BuildDecision as BuildDecisionType } from "../types";
import UserInsightForm from "./UserInsightForm";

interface BuildDecisionProps {
  data: BuildReviewData;
  onSubmit: (input: UserInput) => void;
}

export default function BuildDecision({ data, onSubmit }: BuildDecisionProps) {
  const { t } = useTranslation();
  const [showInsightForm, setShowInsightForm] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [selectedClaimId, setSelectedClaimId] = useState<string>("");

  const handleDecision = (decision: BuildDecisionType) => {
    if (decision === "deep_dive") {
      if (!selectedClaimId) {
        alert(t("build.selectClaim"));
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
      {data.gaps.length > 0 && (
        <div className="bg-white border border-gray-200/80 rounded-xl shadow-md shadow-gray-200/40 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">
            {t("build.gaps")}
          </h3>
          <ul className="space-y-2">
            {data.gaps.map((gap, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-blue-500 text-sm mt-0.5">&#9650;</span>
                <span className="text-gray-600 text-sm">{gap}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => handleDecision("continue")}
            disabled={data.max_rounds_reached}
            className={`py-2.5 px-4 rounded-md font-medium text-sm transition-colors ${
              data.max_rounds_reached
                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-500 text-white"
            }`}
          >
            {t("build.continue")}
          </button>
          <button
            onClick={() => handleDecision("resolve")}
            className="bg-blue-600 hover:bg-blue-500 text-white py-2.5 px-4 rounded-md font-medium text-sm transition-colors"
          >
            {t("build.resolve")}
          </button>
        </div>

        <div className="bg-white border border-gray-200/80 rounded-xl shadow-md shadow-gray-200/40">
          <button
            onClick={() => setAdvancedOpen(!advancedOpen)}
            className="w-full flex items-center gap-2 px-4 py-3 text-sm text-gray-600 hover:text-gray-800 transition-colors"
          >
            <span className={`transition-transform ${advancedOpen ? "rotate-90" : ""}`}>&#9654;</span>
            {t("build.advancedOptions")}
          </button>
          {advancedOpen && (
            <div className="px-4 pb-4 space-y-3">
              <div>
                <label className="block text-xs text-gray-500 mb-2">
                  {t("build.deepDive")}
                </label>
                <div className="flex gap-2">
                  <select
                    value={selectedClaimId}
                    onChange={(e) => setSelectedClaimId(e.target.value)}
                    disabled={data.max_rounds_reached}
                    className="flex-1 bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <option value="">{t("build.selectClaim")}</option>
                    {data.graph.nodes.map((node) => (
                      <option key={node.id} value={node.id}>
                        {(node.data?.claim_text ?? "").slice(0, 60)}...
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => handleDecision("deep_dive")}
                    disabled={data.max_rounds_reached || !selectedClaimId}
                    className="bg-blue-500 hover:bg-blue-400 text-white py-2 px-4 rounded-md font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {t("build.deepDiveAction")}
                  </button>
                </div>
              </div>
              <button
                onClick={() => handleDecision("add_insight")}
                className="w-full bg-blue-500 hover:bg-blue-400 text-white py-2.5 px-4 rounded-md font-medium text-sm transition-colors"
              >
                {t("build.addInsight")}
              </button>
            </div>
          )}
        </div>
      </div>

      {data.max_rounds_reached && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-blue-700 text-sm">
            {t("build.maxRounds")}
          </p>
        </div>
      )}
    </div>
  );
}
