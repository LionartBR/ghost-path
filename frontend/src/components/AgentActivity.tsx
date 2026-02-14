import React, { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

interface ToolCall {
  tool: string;
  input_preview: string;
}

interface ToolError {
  tool: string;
  error_code: string;
  message: string;
}

interface AgentActivityProps {
  isStreaming: boolean;
  agentText: string[];
  toolCalls: ToolCall[];
  toolErrors: ToolError[];
}

export const AgentActivity: React.FC<AgentActivityProps> = ({
  isStreaming,
  agentText,
  toolCalls,
  toolErrors,
}) => {
  const { t } = useTranslation();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [agentText, toolCalls, toolErrors]);

  const hasActivity = agentText.length > 0 || toolCalls.length > 0 || toolErrors.length > 0;

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm h-96 flex flex-col">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-900">{t("agent.title")}</h3>
        {isStreaming && (
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full" />
            <span className="text-xs text-green-600 font-medium">
              {hasActivity ? t("agent.processing") : t("agent.thinking")}
            </span>
          </div>
        )}
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-5 py-3 space-y-1"
      >
        {!hasActivity && (
          <div className="h-full flex items-center justify-center text-gray-400 text-sm">
            {t("agent.waiting")}
          </div>
        )}

        {agentText.map((text, i) => (
          <div key={`text-${i}`} className="flex items-start gap-2.5 py-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 flex-shrink-0" />
            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{text}</p>
          </div>
        ))}

        {toolCalls.map((call, i) => (
          <div key={`tool-${i}`} className="flex items-start gap-2.5 py-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-purple-500 mt-1.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <span className="text-xs font-mono text-purple-600 font-semibold">{call.tool}</span>
              <p className="text-xs text-gray-400 mt-0.5 truncate">{call.input_preview}</p>
            </div>
          </div>
        ))}

        {toolErrors.map((error, i) => (
          <div key={`error-${i}`} className="flex items-start gap-2.5 py-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-red-500 mt-1.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <span className="text-xs font-mono text-red-600 font-semibold">{error.tool}</span>
              <span className="text-xs text-red-500 ml-2 font-medium">{error.error_code}</span>
              <p className="text-xs text-gray-500 mt-0.5">{error.message}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
