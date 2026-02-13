import { useState } from "react";
import type { Evidence } from "../types";

interface EvidencePanelProps {
  evidence: Evidence[];
}

const EVIDENCE_TYPE_COLORS: Record<
  string,
  { bg: string; text: string }
> = {
  supporting: { bg: "bg-green-600", text: "text-green-100" },
  contradicting: { bg: "bg-red-600", text: "text-red-100" },
  contextual: { bg: "bg-blue-600", text: "text-blue-100" },
};

export default function EvidencePanel({ evidence }: EvidencePanelProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-750 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold text-white">Evidence</span>
          <span className="px-2 py-1 bg-gray-700 text-gray-300 rounded text-sm">
            {evidence.length}
          </span>
        </div>
        <svg
          className={`w-5 h-5 text-gray-400 transition-transform ${
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
        <div className="border-t border-gray-700 p-4 space-y-3 max-h-96 overflow-y-auto">
          {evidence.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-4">
              No evidence available yet.
            </p>
          ) : (
            evidence.map((item, idx) => (
              <div
                key={idx}
                className="bg-gray-900 rounded-lg p-3 border border-gray-700"
              >
                <div className="flex items-start justify-between mb-2">
                  {item.url ? (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300 font-medium text-sm underline flex-1"
                    >
                      {item.title}
                    </a>
                  ) : (
                    <span className="text-white font-medium text-sm flex-1">
                      {item.title}
                    </span>
                  )}
                  {item.type && (
                    <span
                      className={`ml-2 px-2 py-1 rounded text-xs font-semibold ${
                        EVIDENCE_TYPE_COLORS[item.type]?.bg || "bg-gray-600"
                      } ${EVIDENCE_TYPE_COLORS[item.type]?.text || "text-gray-100"}`}
                    >
                      {item.type}
                    </span>
                  )}
                </div>
                <p className="text-gray-300 text-sm leading-relaxed">
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
