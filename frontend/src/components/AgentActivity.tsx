/**AgentActivity — streaming agent output with markdown rendering and tool call tags.
 *
 * Invariants:
 *   - Consecutive agent_text chunks are pre-merged in useAgentStream (single ActivityItem)
 *   - Text blocks rendered as markdown; tool calls as compact inline tags
 *   - Auto-scrolls to bottom on new content
 *
 * Design Decisions:
 *   - ReactMarkdown reuses KnowledgeDocument styling scaled for activity panel (ADR: consistency)
 *   - Streaming state indicated by pulsing green dot in header
 */

import React, { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ActivityItem } from "../types";

interface AgentActivityProps {
  isStreaming: boolean;
  activityItems: ActivityItem[];
}

export const AgentActivity: React.FC<AgentActivityProps> = ({
  isStreaming,
  activityItems,
}) => {
  const { t } = useTranslation();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [activityItems]);

  const hasActivity = activityItems.length > 0;

  return (
    <div className="bg-white border border-gray-200/80 rounded-xl shadow-md shadow-gray-200/40 h-96 flex flex-col">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-900">{t("agent.title")}</h3>
        {isStreaming && (
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-xs font-medium animate-shimmer-green">
              {hasActivity ? t("agent.processing") : t("agent.thinking")}
            </span>
          </div>
        )}
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-5 py-3 space-y-3"
      >
        {!hasActivity && (
          <div className="h-full flex items-center justify-center text-gray-400 text-sm">
            {t("agent.waiting")}
          </div>
        )}

        {activityItems.map((item, i) => {
          switch (item.kind) {
            case "text":
              return (
                <div key={i} className="agent-markdown animate-fade-in">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      h1: ({ children }) => (
                        <h1 className="text-base font-bold text-gray-900 mb-2 mt-3 first:mt-0">{children}</h1>
                      ),
                      h2: ({ children }) => (
                        <h2 className="text-sm font-bold text-gray-800 mb-1.5 mt-3 first:mt-0">{children}</h2>
                      ),
                      h3: ({ children }) => (
                        <h3 className="text-sm font-semibold text-gray-800 mb-1 mt-2">{children}</h3>
                      ),
                      p: ({ children }) => (
                        <p className="text-sm text-gray-700 leading-relaxed mb-2 last:mb-0">{children}</p>
                      ),
                      ul: ({ children }) => (
                        <ul className="list-disc list-outside ml-4 text-sm text-gray-700 mb-2 space-y-0.5">{children}</ul>
                      ),
                      ol: ({ children }) => (
                        <ol className="list-decimal list-outside ml-4 text-sm text-gray-700 mb-2 space-y-0.5">{children}</ol>
                      ),
                      li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                      strong: ({ children }) => (
                        <strong className="font-semibold text-gray-900">{children}</strong>
                      ),
                      em: ({ children }) => (
                        <em className="italic text-gray-600">{children}</em>
                      ),
                      blockquote: ({ children }) => (
                        <blockquote className="border-l-3 border-indigo-300 pl-3 italic text-gray-500 my-2 text-sm">{children}</blockquote>
                      ),
                      code: ({ children }) => (
                        <code className="bg-gray-100 text-indigo-700 px-1 py-0.5 rounded text-xs font-mono">{children}</code>
                      ),
                      pre: ({ children }) => (
                        <pre className="bg-gray-50 border border-gray-200 p-3 rounded-md overflow-x-auto mb-2 text-xs">{children}</pre>
                      ),
                      a: ({ href, children }) => (
                        <a
                          href={href}
                          className="text-indigo-600 hover:text-indigo-500 underline decoration-indigo-300"
                          target="_blank"
                          rel="noopener noreferrer"
                        >{children}</a>
                      ),
                      table: ({ children }) => (
                        <div className="overflow-x-auto mb-2">
                          <table className="min-w-full text-sm border-collapse">{children}</table>
                        </div>
                      ),
                      thead: ({ children }) => (
                        <thead className="bg-gray-50">{children}</thead>
                      ),
                      th: ({ children }) => (
                        <th className="px-2 py-1 text-left text-xs font-semibold text-gray-600 border-b border-gray-200">{children}</th>
                      ),
                      td: ({ children }) => (
                        <td className="px-2 py-1 text-sm text-gray-700 border-b border-gray-100">{children}</td>
                      ),
                    }}
                  >
                    {item.text}
                  </ReactMarkdown>
                </div>
              );
            case "tool_call":
              return (
                <div key={i} className="flex items-center gap-2 py-1 animate-fade-in">
                  <div className="flex items-center gap-1.5 px-2.5 py-1 bg-purple-50 border border-purple-200 rounded-full">
                    <div className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
                    <span className="text-xs font-mono text-purple-700 font-medium">{item.tool}</span>
                  </div>
                  {item.input_preview && (
                    <span className="text-xs text-gray-400 truncate max-w-[200px]">{item.input_preview}</span>
                  )}
                </div>
              );
            case "tool_error":
              return (
                <div key={i} className="flex items-start gap-2 py-1 animate-fade-in">
                  <div className="flex items-center gap-1.5 px-2.5 py-1 bg-red-50 border border-red-200 rounded-full flex-shrink-0">
                    <div className="w-1.5 h-1.5 rounded-full bg-red-400" />
                    <span className="text-xs font-mono text-red-700 font-medium">{item.tool}</span>
                  </div>
                  <div className="min-w-0 pt-0.5">
                    <span className="text-xs text-red-600 font-semibold">{item.error_code}</span>
                    <p className="text-xs text-gray-500 mt-0.5">{item.message}</p>
                  </div>
                </div>
              );
          }
        })}
      </div>
    </div>
  );
};
