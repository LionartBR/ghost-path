import { useState } from "react";
import { useTranslation } from "react-i18next";

interface Props {
  onSubmit: (problem: string) => void;
  loading: boolean;
  exampleProblem?: string;
}

export function ProblemInput({ onSubmit, loading, exampleProblem }: Props) {
  const { t } = useTranslation();
  const [problem, setProblem] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (problem.trim().length >= 10) onSubmit(problem.trim());
  };

  const charCount = problem.length;
  const isTooShort = charCount > 0 && charCount < 10;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label
          htmlFor="problem"
          className="block text-sm font-medium text-gray-700 mb-2"
        >
          {t("problemInput.label")}
        </label>
        <textarea
          id="problem"
          value={problem}
          onChange={(e) => setProblem(e.target.value)}
          className="w-full p-4 bg-gray-50/30 border border-gray-200 text-gray-900 rounded-xl
                     text-sm resize-none focus:ring-2 focus:ring-indigo-400/50
                     focus:border-indigo-300 placeholder-gray-400 transition-all
                     hover:border-gray-300"
          style={{ height: 136 }}
          placeholder={t("problemInput.placeholder")}
          disabled={loading}
        />
        <div className="flex items-center justify-between mt-1.5">
          <span
            className={`text-xs ${
              isTooShort ? "text-amber-500" : "text-gray-400"
            }`}
          >
            {charCount}/10000{isTooShort && ` — ${t("problemInput.minChars", { count: 10 })}`}
          </span>
        </div>
      </div>

      {exampleProblem && (
        <button
          type="button"
          onClick={() => setProblem(exampleProblem)}
          className="w-full text-left px-4 py-3 bg-indigo-50/70 hover:bg-indigo-50
                     rounded-xl text-sm transition-all group border border-indigo-100/60
                     hover:border-indigo-200/80"
        >
          <span className="text-indigo-400 text-xs font-medium uppercase tracking-wide">
            {t("problemInput.tryExample")}
          </span>
          <p className="text-indigo-700 mt-1 leading-snug">
            &ldquo;{exampleProblem}&rdquo;
          </p>
        </button>
      )}

      <button
        type="submit"
        disabled={loading || problem.trim().length < 10}
        className="w-full py-3.5 bg-indigo-600 text-white font-semibold rounded-xl
                   hover:bg-indigo-700 active:bg-indigo-800
                   shadow-md shadow-indigo-200/50 hover:shadow-lg hover:shadow-indigo-300/50
                   disabled:bg-gray-100 disabled:text-gray-400 disabled:shadow-none
                   disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <svg
              className="animate-spin h-4 w-4"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            {t("problemInput.creating")}
          </>
        ) : (
          t("problemInput.submit")
        )}
      </button>
    </form>
  );
}
