interface Props {
  specContent: string | null;
  downloadUrl: string | null;
}

export function SpecDownload({ specContent, downloadUrl }: Props) {
  if (!specContent) return null;

  return (
    <div className="space-y-4">
      <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">
          Final Spec Generated
        </h2>
        <div className="prose prose-sm max-w-none font-mono text-gray-700 whitespace-pre-wrap max-h-[500px] overflow-y-auto">
          {specContent}
        </div>
      </div>

      {downloadUrl && (
        <a
          href={downloadUrl}
          download
          className="inline-block px-6 py-3 bg-gray-900 text-white
                     font-medium rounded-xl hover:bg-gray-800
                     transition-colors"
        >
          Download Spec (.md)
        </a>
      )}
    </div>
  );
}
