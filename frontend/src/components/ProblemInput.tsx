import { useState } from "react";

interface Props {
  onSubmit: (problem: string) => void;
  loading: boolean;
}

export function ProblemInput({ onSubmit, loading }: Props) {
  const [problem, setProblem] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (problem.trim().length >= 10) onSubmit(problem.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label
          htmlFor="problem"
          className="block text-sm font-medium text-gray-300 mb-2"
        >
          Describe your problem
        </label>
        <textarea
          id="problem"
          value={problem}
          onChange={(e) => setProblem(e.target.value)}
          className="w-full h-40 p-4 border-2 border-gray-700 bg-gray-900 text-gray-200 rounded-xl
                     text-sm resize-none focus:ring-2 focus:ring-blue-500
                     focus:border-transparent placeholder-gray-500"
          placeholder="What complex problem are you trying to solve? Be specific about context, constraints, and what you've already tried..."
          disabled={loading}
        />
        <p className="mt-1 text-xs text-gray-500">
          {problem.length}/10000 characters (minimum 10)
        </p>
      </div>
      <button
        type="submit"
        disabled={loading || problem.trim().length < 10}
        className="w-full py-3 bg-blue-600 text-white font-medium rounded-xl
                   hover:bg-blue-700 disabled:opacity-40
                   disabled:cursor-not-allowed transition-colors"
      >
        {loading ? "Creating session..." : "Start TRIZ"}
      </button>
    </form>
  );
}
