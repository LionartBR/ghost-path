/* KnowledgeDocument — renders final knowledge artifact with download. */
import { useTranslation } from "react-i18next";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface KnowledgeDocumentProps {
  markdown: string;
}

export default function KnowledgeDocument({
  markdown,
}: KnowledgeDocumentProps) {
  const { t } = useTranslation();

  const handleDownload = () => {
    const blob = new Blob([markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `knowledge-document-${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 bg-gray-800 border-b border-gray-700">
        <h2 className="text-lg font-semibold text-gray-100">{t("document.title")}</h2>
        <button
          onClick={handleDownload}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold transition-all duration-200 hover:scale-[1.03] hover:shadow-md active:scale-[0.97]"
        >
          {t("document.download")}
        </button>
      </div>
      <div className="bg-gray-700 p-1.5 md:p-2">
        <div className="bg-white border border-gray-300 rounded-lg px-4 md:px-6 py-6 prose prose-sm max-w-none font-sans tracking-wide mx-auto">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => (
              <h1 className="text-lg font-semibold uppercase tracking-wide text-gray-900 mb-5 pb-2 border-b border-gray-200">
                {children}
              </h1>
            ),
            h2: ({ children }) => (
              <h2 className="text-base font-semibold uppercase tracking-wide text-gray-800 mb-3 mt-8">
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 className="text-[0.9375rem] font-medium tracking-wide text-gray-700 mb-2 mt-5">
                {children}
              </h3>
            ),
            p: ({ children }) => (
              <p className="text-sm text-gray-600 mb-3.5 leading-relaxed tracking-normal">{children}</p>
            ),
            ul: ({ children }) => (
              <ul className="list-disc list-inside text-sm text-gray-600 mb-3.5 space-y-1.5 tracking-normal">
                {children}
              </ul>
            ),
            ol: ({ children }) => (
              <ol className="list-decimal list-inside text-sm text-gray-600 mb-3.5 space-y-1.5 tracking-normal">
                {children}
              </ol>
            ),
            li: ({ children }) => <li className="ml-4 leading-relaxed">{children}</li>,
            blockquote: ({ children }) => (
              <blockquote className="border-l-3 border-gray-300 pl-4 italic text-sm text-gray-400 my-4 tracking-normal">
                {children}
              </blockquote>
            ),
            code: ({ children }) => (
              <code className="bg-gray-50 text-gray-700 px-1.5 py-0.5 rounded text-sm font-mono tracking-normal">
                {children}
              </code>
            ),
            pre: ({ children }) => (
              <pre className="bg-gray-50 border border-gray-100 p-4 rounded-lg overflow-x-auto mb-4">
                {children}
              </pre>
            ),
            a: ({ href, children }) => (
              <a
                href={href}
                className="text-blue-600 hover:text-blue-500 underline decoration-blue-300"
                target="_blank"
                rel="noopener noreferrer"
              >
                {children}
              </a>
            ),
            table: ({ children }) => (
              <div className="overflow-x-auto mb-4">
                <table className="min-w-full text-sm border-collapse border border-gray-200">{children}</table>
              </div>
            ),
            thead: ({ children }) => (
              <thead className="bg-gray-50">{children}</thead>
            ),
            th: ({ children }) => (
              <th className="px-3 py-2 text-left text-sm font-semibold uppercase tracking-wide text-gray-500 border-b border-gray-200">{children}</th>
            ),
            td: ({ children }) => (
              <td className="px-3 py-2 text-sm text-gray-600 border-b border-gray-100">{children}</td>
            ),
          }}
        >
          {markdown}
        </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
