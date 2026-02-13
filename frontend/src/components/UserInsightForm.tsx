import { useState } from "react";

interface UserInsightFormProps {
  onSubmit: (insight: string, urls: string[]) => void;
  onCancel: () => void;
}

export default function UserInsightForm({ onSubmit, onCancel }: UserInsightFormProps) {
  const [insight, setInsight] = useState("");
  const [urls, setUrls] = useState<string[]>([""]);

  const addUrlField = () => {
    setUrls([...urls, ""]);
  };

  const removeUrlField = (index: number) => {
    setUrls(urls.filter((_, i) => i !== index));
  };

  const updateUrl = (index: number, value: string) => {
    const updated = [...urls];
    updated[index] = value;
    setUrls(updated);
  };

  const handleSubmit = () => {
    if (!insight.trim()) {
      alert("Please enter an insight");
      return;
    }
    const filteredUrls = urls.filter((url) => url.trim() !== "");
    onSubmit(insight, filteredUrls);
  };

  return (
    <div className="space-y-6">
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
        <h2 className="text-xl font-semibold text-white mb-2">
          Add Your Own Insight
        </h2>
        <p className="text-gray-400 text-sm">
          Contribute your own knowledge claim with supporting evidence URLs.
        </p>
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 space-y-4">
        <div>
          <label className="block text-sm text-gray-400 mb-2">
            Your insight or claim
          </label>
          <textarea
            value={insight}
            onChange={(e) => setInsight(e.target.value)}
            placeholder="Describe your insight, claim, or hypothesis..."
            rows={6}
            className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm text-gray-400">
              Supporting evidence URLs
            </label>
            <button
              onClick={addUrlField}
              className="text-blue-400 hover:text-blue-300 text-sm font-medium"
            >
              + Add URL
            </button>
          </div>
          <div className="space-y-2">
            {urls.map((url, i) => (
              <div key={i} className="flex gap-2">
                <input
                  type="text"
                  value={url}
                  onChange={(e) => updateUrl(i, e.target.value)}
                  placeholder="https://..."
                  className="flex-1 bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {urls.length > 1 && (
                  <button
                    onClick={() => removeUrlField(i)}
                    className="bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded text-sm font-medium transition-colors"
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex gap-3">
        <button
          onClick={handleSubmit}
          className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg transition-colors"
        >
          Submit Insight
        </button>
        <button
          onClick={onCancel}
          className="flex-1 bg-gray-700 hover:bg-gray-600 text-white font-medium py-3 px-6 rounded-lg transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
