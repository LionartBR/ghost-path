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
          className="block text-sm font-medium text-gray-700 mb-2"
        >
          Describe your problem
        </label>
        <textarea
          id="problem"
          value={problem}
          onChange={(e) => setProblem(e.target.value)}
          className="w-full h-40 p-4 border-2 border-gray-200 rounded-xl
                     text-sm resize-none focus:ring-2 focus:ring-gray-900
                     focus:border-transparent"
          placeholder="What complex problem are you trying to solve? Be specific about context, constraints, and what you've already tried..."
          disabled={loading}
        />
        <p className="mt-1 text-xs text-gray-400">
          {problem.length}/10000 characters (minimum 10)
        </p>
      </div>
      <button
        type="submit"
        disabled={loading || problem.trim().length < 10}
        className="w-full py-3 bg-gray-900 text-white font-medium rounded-xl
                   hover:bg-gray-800 disabled:opacity-40
                   disabled:cursor-not-allowed transition-colors"
      >
        {loading ? "Creating session..." : "Start GhostPath"}
      </button>
    </form>
  );
}
