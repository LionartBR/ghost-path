interface Props {
  isStreaming: boolean;
  toolCalls: { tool: string; input_preview: string }[];
  agentText: string[];
}

export function AgentActivityIndicator({
  isStreaming,
  toolCalls,
  agentText,
}: Props) {
  if (!isStreaming && toolCalls.length === 0 && agentText.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      {isStreaming && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span className="inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          Agent is working...
        </div>
      )}

      {agentText.length > 0 && (
        <div className="bg-gray-50 rounded-xl p-4 font-mono text-sm whitespace-pre-wrap text-gray-700 max-h-96 overflow-y-auto">
          {agentText.join("")}
        </div>
      )}

      {toolCalls.length > 0 && (
        <div className="space-y-1">
          {toolCalls.slice(-5).map((tc, i) => (
            <div
              key={i}
              className="text-xs text-gray-400 flex items-center gap-2"
            >
              <span className="font-mono bg-gray-100 px-1.5 py-0.5 rounded">
                {tc.tool}
              </span>
              <span className="truncate">{tc.input_preview.slice(0, 80)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
