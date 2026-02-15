import { useState } from "react";
import { useTranslation } from "react-i18next";

interface UserInsightFormProps {
  onSubmit: (insight: string, urls: string[]) => void;
  onCancel: () => void;
}

export default function UserInsightForm({ onSubmit, onCancel }: UserInsightFormProps) {
  const { t } = useTranslation();
  const [insight, setInsight] = useState("");
  const [urls, setUrls] = useState<string[]>([""]);
  const [error, setError] = useState("");

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
      setError(t("insight.required"));
      return;
    }
    setError("");
    const filteredUrls = urls.filter((url) => url.trim() !== "");
    onSubmit(insight, filteredUrls);
  };

  return (
    <div className="space-y-5">
      <div className="bg-white border border-gray-200/80 rounded-xl shadow-md shadow-gray-200/40 p-5">
        <h2 className="text-base font-semibold text-gray-900 mb-1">
          {t("insight.title")}
        </h2>
        <p className="text-gray-500 text-sm">
          {t("insight.description")}
        </p>
      </div>

      <div className="bg-white border border-gray-200/80 rounded-xl shadow-md shadow-gray-200/40 p-5 space-y-4">
        <div>
          <label className="block text-xs text-gray-500 mb-2">
            {t("insight.label")}
          </label>
          <textarea
            value={insight}
            onChange={(e) => setInsight(e.target.value)}
            placeholder={t("insight.placeholder")}
            rows={6}
            className="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none placeholder-gray-400"
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-xs text-gray-500">
              {t("insight.urlLabel")}
            </label>
            <button
              onClick={addUrlField}
              className="text-blue-600 hover:text-blue-500 text-xs font-medium"
            >
              {t("insight.addUrl")}
            </button>
          </div>
          <div className="space-y-2">
            {urls.map((url, i) => (
              <div key={i} className="flex gap-2">
                <input
                  type="text"
                  value={url}
                  onChange={(e) => updateUrl(i, e.target.value)}
                  placeholder={t("insight.urlPlaceholder")}
                  className="flex-1 bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-400"
                />
                {urls.length > 1 && (
                  <button
                    onClick={() => removeUrlField(i)}
                    className="bg-white border border-gray-200 hover:bg-blue-50 hover:border-blue-200 text-gray-500 hover:text-blue-600 px-3 py-2 rounded-md text-xs font-medium transition-colors"
                  >
                    {t("insight.remove")}
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-4 py-2">{error}</p>
      )}

      <div className="flex gap-3">
        <button
          onClick={handleSubmit}
          className="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm py-3 px-6 rounded-lg transition-all"
        >
          {t("insight.submit")}
        </button>
        <button
          onClick={onCancel}
          className="flex-1 bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 font-medium text-sm py-2.5 px-6 rounded-md transition-colors"
        >
          {t("insight.cancel")}
        </button>
      </div>
    </div>
  );
}
