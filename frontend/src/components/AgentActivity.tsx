import React, { useEffect, useRef } from "react";

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
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [agentText, toolCalls, toolErrors]);

  const hasActivity = agentText.length > 0 || toolCalls.length > 0 || toolErrors.length > 0;

  return (
    <div className="bg-gray-800 rounded-lg p-4 h-96 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-bold text-white">Agent Activity</h3>
        {isStreaming && (
          <div className="flex items-center gap-2">
            <div className="relative">
              <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" />
              <div className="absolute inset-0 w-3 h-3 bg-green-500 rounded-full animate-ping opacity-75" />
            </div>
            <span className="text-green-400 text-sm font-medium">Streaming</span>
          </div>
        )}
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-3 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-900"
      >
        {!hasActivity && (
          <div className="h-full flex items-center justify-center text-gray-500">
            Waiting for agent activity...
          </div>
        )}

        {agentText.map((text, i) => (
          <div key={`text-${i}`} className="p-3 bg-gray-900 rounded border-l-4 border-blue-500">
            <div className="flex items-start gap-2">
              <svg className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z" />
                <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z" />
              </svg>
              <p className="text-gray-300 text-sm whitespace-pre-wrap">{text}</p>
            </div>
          </div>
        ))}

        {toolCalls.map((call, i) => (
          <div key={`tool-${i}`} className="p-3 bg-gray-900 rounded border-l-4 border-purple-500">
            <div className="flex items-start gap-2">
              <svg className="w-5 h-5 text-purple-400 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
              </svg>
              <div className="flex-1">
                <p className="text-purple-300 font-mono text-sm font-bold">{call.tool}</p>
                <p className="text-gray-400 text-xs mt-1">{call.input_preview}</p>
              </div>
            </div>
          </div>
        ))}

        {toolErrors.map((error, i) => (
          <div key={`error-${i}`} className="p-3 bg-red-900/20 rounded border-l-4 border-red-500">
            <div className="flex items-start gap-2">
              <svg className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div className="flex-1">
                <p className="text-red-300 font-mono text-sm font-bold">{error.tool}</p>
                <p className="text-red-400 text-xs mt-1 font-semibold">{error.error_code}</p>
                <p className="text-gray-300 text-xs mt-1">{error.message}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
