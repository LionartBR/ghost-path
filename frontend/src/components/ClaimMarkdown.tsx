/* ClaimMarkdown — lightweight markdown renderer for claim detail fields.

Invariants:
    - Reuses react-markdown + remark-gfm (already in deps)
    - Compact styling (text-xs/text-sm) suited for expandable detail sections
    - Used by VerdictPanel, ClaimCard, ClaimReview for reasoning/score_reasoning/falsifiability

Design Decisions:
    - Extracted component over inline ReactMarkdown: avoids duplicating component map in 3+ files
    - Inherits parent text color via className prop (default: text-gray-500 text-xs)
*/

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ClaimMarkdownProps {
  children: string;
  className?: string;
}

export default function ClaimMarkdown({ children, className = "text-xs text-gray-500 leading-relaxed" }: ClaimMarkdownProps) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="mb-1.5 last:mb-0">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold text-gray-700">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          ul: ({ children }) => <ul className="list-disc list-outside ml-3 mb-1.5 space-y-0.5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal list-outside ml-3 mb-1.5 space-y-0.5">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          a: ({ href, children }) => (
            <a href={href} className="text-blue-500 hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>
          ),
          code: ({ children }) => <code className="bg-gray-100 text-gray-700 px-0.5 rounded text-[10px] font-mono">{children}</code>,
          blockquote: ({ children }) => <blockquote className="border-l-2 border-gray-300 pl-2 italic my-1">{children}</blockquote>,
          h1: ({ children }) => <p className="font-bold text-gray-700 mb-1">{children}</p>,
          h2: ({ children }) => <p className="font-bold text-gray-700 mb-1">{children}</p>,
          h3: ({ children }) => <p className="font-semibold text-gray-700 mb-0.5">{children}</p>,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
