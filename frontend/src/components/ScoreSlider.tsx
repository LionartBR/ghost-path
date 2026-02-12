interface Props {
  value: number | undefined;
  onChange: (score: number) => void;
}

export function ScoreSlider({ value, onChange }: Props) {
  const displayValue = value ?? 5.0;

  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-400 w-6">0</span>
      <input
        type="range"
        min="0"
        max="10"
        step="0.1"
        value={displayValue}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none
                   cursor-pointer accent-gray-900"
      />
      <span className="text-xs text-gray-400 w-6">10</span>
      <span className="text-sm font-mono font-bold text-gray-900 w-10 text-right">
        {displayValue.toFixed(1)}
      </span>
    </div>
  );
}
