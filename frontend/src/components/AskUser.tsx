import { useState } from "react";
import type { AskUserData } from "../types";

interface Props {
  data: AskUserData;
  onRespond: (response: string) => void;
}

export function AskUser({ data, onRespond }: Props) {
  const [freeText, setFreeText] = useState("");
  const [selectedOption, setSelectedOption] = useState<string | null>(null);

  const handleSubmit = () => {
    const response =
      selectedOption === "__free_text__" ? freeText : selectedOption;
    if (response) onRespond(response);
  };

  return (
    <div className="rounded-2xl border-2 border-blue-200 bg-blue-50/50 p-6 space-y-4">
      {data.context && (
        <div className="text-sm text-gray-600 bg-white rounded-lg p-4 border border-gray-100">
          {data.context}
        </div>
      )}

      <h3 className="text-lg font-semibold text-gray-900">{data.question}</h3>

      <div className="space-y-2">
        {data.options.map((opt) => (
          <button
            key={opt.label}
            onClick={() => setSelectedOption(opt.label)}
            className={`w-full text-left px-4 py-3 rounded-xl border-2 transition-all
              ${
                selectedOption === opt.label
                  ? "border-blue-500 bg-blue-50 ring-2 ring-blue-200"
                  : "border-gray-200 bg-white hover:border-gray-300"
              }`}
          >
            <span className="font-medium text-gray-900">{opt.label}</span>
            {opt.description && (
              <span className="block text-sm text-gray-500 mt-0.5">
                {opt.description}
              </span>
            )}
          </button>
        ))}

        {data.allow_free_text !== false && (
          <div>
            <button
              onClick={() => setSelectedOption("__free_text__")}
              className={`w-full text-left px-4 py-3 rounded-xl border-2 transition-all
                ${
                  selectedOption === "__free_text__"
                    ? "border-blue-500 bg-blue-50 ring-2 ring-blue-200"
                    : "border-gray-200 bg-white hover:border-gray-300"
                }`}
            >
              <span className="font-medium text-gray-500">
                Type my own response...
              </span>
            </button>

            {selectedOption === "__free_text__" && (
              <textarea
                value={freeText}
                onChange={(e) => setFreeText(e.target.value)}
                className="w-full mt-2 p-3 border-2 border-blue-300 rounded-xl
                           text-sm resize-none focus:ring-2 focus:ring-blue-500
                           focus:border-transparent"
                rows={3}
                placeholder="Your response..."
                autoFocus
              />
            )}
          </div>
        )}
      </div>

      <button
        onClick={handleSubmit}
        disabled={
          !selectedOption ||
          (selectedOption === "__free_text__" && !freeText.trim())
        }
        className="w-full py-3 bg-blue-600 text-white font-medium rounded-xl
                   hover:bg-blue-700 disabled:opacity-40
                   disabled:cursor-not-allowed transition-colors"
      >
        Submit response
      </button>
    </div>
  );
}
