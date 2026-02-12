import { useState } from "react";
import type { Premise, PremiseScore } from "../types";
import { PremiseCard } from "./PremiseCard";

interface Props {
  premises: Premise[];
  roundNumber: number;
  onSubmitScores: (scores: PremiseScore[]) => void;
  onResolve: (winnerIndex: number) => void;
  isStreaming: boolean;
}

export function RoundView({
  premises,
  roundNumber,
  onSubmitScores,
  onResolve,
  isStreaming,
}: Props) {
  const [scores, setScores] = useState<Record<number, number>>({});
  const [comments, setComments] = useState<Record<number, string>>({});
  const [resolveMode, setResolveMode] = useState(false);

  const allScored = premises.every((_, i) => scores[i] !== undefined);

  const handleNextRound = () => {
    const result: PremiseScore[] = premises.map((p, i) => ({
      premise_title: p.title,
      score: scores[i] ?? 5.0,
      comment: comments[i] || undefined,
    }));
    onSubmitScores(result);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">
          Round {roundNumber}
        </h2>
        <span className="text-sm text-gray-500">
          Rate each premise from 0.0 to 10.0
        </span>
      </div>

      <div className="space-y-4">
        {premises.map((premise, index) => (
          <PremiseCard
            key={premise.title}
            premise={premise}
            isStreaming={isStreaming}
            onScore={(score) =>
              setScores((prev) => ({ ...prev, [index]: score }))
            }
            onComment={(comment) =>
              setComments((prev) => ({ ...prev, [index]: comment }))
            }
          />
        ))}
      </div>

      {!isStreaming && (
        <div className="flex gap-3">
          <button
            onClick={handleNextRound}
            disabled={!allScored}
            className="flex-1 py-3 bg-gray-900 text-white font-medium
                       rounded-xl hover:bg-gray-800 disabled:opacity-40
                       transition-colors"
          >
            Next Round
          </button>

          {!resolveMode ? (
            <button
              onClick={() => setResolveMode(true)}
              className="px-6 py-3 bg-green-600 text-white font-medium
                         rounded-xl hover:bg-green-700 transition-colors"
            >
              Problem Resolved
            </button>
          ) : (
            <div className="flex-1 p-4 bg-green-50 border-2 border-green-200 rounded-xl space-y-3">
              <p className="text-sm font-medium text-green-800">
                Which premise solves your problem?
              </p>
              {premises.map((p, i) => (
                <button
                  key={i}
                  onClick={() => onResolve(i)}
                  className="w-full text-left px-4 py-2 bg-white
                             border border-green-300 rounded-lg
                             hover:bg-green-50 transition-colors"
                >
                  <span className="font-medium">{p.title}</span>
                  {scores[i] !== undefined && (
                    <span className="ml-2 text-sm text-gray-500">
                      ({scores[i].toFixed(1)})
                    </span>
                  )}
                </button>
              ))}
              <button
                onClick={() => setResolveMode(false)}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
