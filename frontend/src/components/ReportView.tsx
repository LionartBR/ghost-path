/* ReportView — displays the final spec as rendered markdown. */

interface Props {
  content: string;
}

export function ReportView({ content }: Props) {
  return (
    <div className="bg-white border-2 border-gray-200 rounded-xl p-8">
      <div className="prose prose-sm max-w-none whitespace-pre-wrap">
        {content}
      </div>
    </div>
  );
}
