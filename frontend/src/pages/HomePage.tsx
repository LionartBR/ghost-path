import { useNavigate } from "react-router-dom";
import { ProblemInput } from "../components/ProblemInput";
import { useSession } from "../hooks/useSession";

export function HomePage() {
  const navigate = useNavigate();
  const { loading, error, create } = useSession();

  const handleSubmit = async (problem: string) => {
    const session = await create(problem);
    if (session) {
      navigate(`/session/${session.id}`);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-2xl space-y-8">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-gray-900">GhostPath</h1>
          <p className="text-gray-500">
            Evolutionary idea generation powered by Claude
          </p>
        </div>

        <ProblemInput onSubmit={handleSubmit} loading={loading} />

        {error && (
          <p className="text-sm text-red-600 text-center">{error}</p>
        )}
      </div>
    </div>
  );
}
