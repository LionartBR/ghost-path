import { useState, useEffect, useRef } from "react";

interface Props {
  onSubmit: (problem: string) => void;
  loading: boolean;
  exampleProblem?: string;
}

export function ProblemInput({ onSubmit, loading, exampleProblem }: Props) {
  const [problem, setProblem] = useState("");
  const [showExample, setShowExample] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isValid = problem.trim().length >= 10;

  useEffect(() => {
    if (problem.length > 0) setShowExample(false);
  }, [problem]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isValid) onSubmit(problem.trim());
  };

  const handleExampleClick = () => {
    if (exampleProblem) {
      setProblem(exampleProblem);
      setShowExample(false);
      textareaRef.current?.focus();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="relative">
        <textarea
          ref={textareaRef}
          id="problem"
          value={problem}
          onChange={(e) => setProblem(e.target.value)}
          className="w-full h-36 p-4 bg-gray-50/50 border border-gray-200 text-gray-900 rounded-xl
                     text-sm leading-relaxed resize-none
                     focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400
                     focus:bg-white placeholder-gray-400 transition-all duration-200"
          placeholder="Describe a complex problem you want to investigate..."
          disabled={loading}
        />
        <div className="flex items-center justify-between mt-2">
          <p className="text-xs text-gray-400">
            <span className={problem.length >= 10 ? "text-gray-500" : ""}>{problem.length}</span>
            <span className="text-gray-300">/10000</span>
            {problem.length > 0 && problem.length < 10 && (
              <span className="text-amber-500 ml-2">at least 10 characters</span>
            )}
          </p>
        </div>
      </div>

      {/* Example suggestion */}
      {showExample && exampleProblem && (
        <button
          type="button"
          onClick={handleExampleClick}
          className="w-full text-left px-4 py-3 rounded-xl bg-indigo-50/50 border border-indigo-100
                     hover:bg-indigo-50 transition-all duration-200 group"
        >
          <span className="text-[11px] font-medium text-indigo-400 uppercase tracking-wider">
            Try an example
          </span>
          <p className="text-sm text-indigo-600/80 mt-0.5 group-hover:text-indigo-700 transition-colors">
            "{exampleProblem}"
          </p>
        </button>
      )}

      <button
        type="submit"
        disabled={loading || !isValid}
        className="w-full py-3 bg-indigo-600 text-white font-medium text-sm rounded-xl
                   hover:bg-indigo-700 active:bg-indigo-800
                   disabled:bg-gray-100 disabled:text-gray-400
                   disabled:border disabled:border-gray-200
                   shadow-sm hover:shadow-md disabled:shadow-none
                   transition-all duration-200 cursor-pointer disabled:cursor-not-allowed"
      >
        {loading ? (
          <span className="inline-flex items-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Creating session...
          </span>
        ) : (
          "Start Investigation"
        )}
      </button>
    </form>
  );
}
