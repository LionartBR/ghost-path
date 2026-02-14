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
      alert(t("insight.required"));
      return;
    }
    const filteredUrls = urls.filter((url) => url.trim() !== "");
    onSubmit(insight, filteredUrls);
  };

  return (
    <div className="space-y-5">
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-5">
        <h2 className="text-base font-semibold text-gray-900 mb-1">
          {t("insight.title")}
        </h2>
        <p className="text-gray-500 text-sm">
          {t("insight.description")}
        </p>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-5 space-y-4">
        <div>
          <label className="block text-xs text-gray-500 mb-2">
            {t("insight.label")}
          </label>
          <textarea
            value={insight}
            onChange={(e) => setInsight(e.target.value)}
            placeholder={t("insight.placeholder")}
            rows={6}
            className="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none placeholder-gray-400"
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-xs text-gray-500">
              {t("insight.urlLabel")}
            </label>
            <button
              onClick={addUrlField}
              className="text-indigo-600 hover:text-indigo-500 text-xs font-medium"
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
                  className="flex-1 bg-white border border-gray-200 rounded-md px-3 py-2 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent placeholder-gray-400"
                />
                {urls.length > 1 && (
                  <button
                    onClick={() => removeUrlField(i)}
                    className="bg-white border border-gray-200 hover:bg-red-50 hover:border-red-200 text-gray-500 hover:text-red-600 px-3 py-2 rounded-md text-xs font-medium transition-colors"
                  >
                    {t("insight.remove")}
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
          className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm py-2.5 px-6 rounded-md transition-colors"
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
