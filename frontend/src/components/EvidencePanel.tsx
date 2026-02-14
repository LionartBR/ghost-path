import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { Evidence } from "../types";

interface EvidencePanelProps {
  evidence: Evidence[];
}

const EVIDENCE_TYPE_COLORS: Record<
  string,
  { bg: string; text: string; border: string }
> = {
  supporting: { bg: "bg-green-50", text: "text-green-700", border: "border-green-200" },
  contradicting: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200" },
  contextual: { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200" },
};

export default function EvidencePanel({ evidence }: EvidencePanelProps) {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="bg-white border border-gray-200/80 rounded-xl shadow-md shadow-gray-200/40 overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-5 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-gray-900">{t("evidence.title")}</span>
          <span className="px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full text-xs font-medium">
            {evidence.length}
          </span>
        </div>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="border-t border-gray-100 p-5 space-y-3 max-h-96 overflow-y-auto">
          {evidence.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-4">
              {t("evidence.empty")}
            </p>
          ) : (
            evidence.map((item, idx) => (
              <div
                key={idx}
                className="bg-gray-50 rounded-md p-3 border border-gray-100"
              >
                <div className="flex items-start justify-between mb-2">
                  {item.url ? (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-600 hover:text-indigo-500 font-medium text-sm flex-1"
                    >
                      {item.title}
                    </a>
                  ) : (
                    <span className="text-gray-900 font-medium text-sm flex-1">
                      {item.title}
                    </span>
                  )}
                  {item.type && (
                    <span
                      className={`ml-2 px-2 py-0.5 rounded text-xs font-medium border ${
                        EVIDENCE_TYPE_COLORS[item.type]?.bg || "bg-gray-100"
                      } ${EVIDENCE_TYPE_COLORS[item.type]?.text || "text-gray-600"} ${
                        EVIDENCE_TYPE_COLORS[item.type]?.border || "border-gray-200"
                      }`}
                    >
                      {item.type}
                    </span>
                  )}
                </div>
                <p className="text-gray-600 text-sm leading-relaxed">
                  {item.summary}
                </p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
