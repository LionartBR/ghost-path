import { useParams } from "react-router-dom";
import { ReportView } from "../components/ReportView";

export function ReportPage() {
  const { sessionId } = useParams<{ sessionId: string }>();

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">
          Session Report
        </h1>
        <ReportView
          content={`Report for session ${sessionId}. Download the spec from the session page.`}
        />
      </div>
    </div>
  );
}
