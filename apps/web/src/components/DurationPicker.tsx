import { useState } from "react";

const PRESETS = [1, 3, 5, 10, 15];

export function DurationPicker({
  minutes,
  onChange,
}: {
  minutes: number;
  onChange: (minutes: number) => void;
}) {
  const [customOpen, setCustomOpen] = useState(!PRESETS.includes(minutes));

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {PRESETS.map((preset) => {
          const selected = !customOpen && minutes === preset;
          return (
            <button
              key={preset}
              type="button"
              onClick={() => {
                setCustomOpen(false);
                onChange(preset);
              }}
              className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${
                selected
                  ? "border-accent-500 bg-accent-500/15 text-accent-400"
                  : "border-white/10 bg-white/5 text-white/70 hover:border-white/20"
              }`}
            >
              {preset} min
            </button>
          );
        })}
        <button
          type="button"
          onClick={() => setCustomOpen(true)}
          className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${
            customOpen
              ? "border-accent-500 bg-accent-500/15 text-accent-400"
              : "border-white/10 bg-white/5 text-white/70 hover:border-white/20"
          }`}
        >
          Custom
        </button>
      </div>

      {customOpen && (
        <input
          type="number"
          min={1}
          max={60}
          autoFocus
          value={minutes}
          onChange={(e) => onChange(Number(e.target.value))}
          className="mt-2 w-32 rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-white"
        />
      )}
    </div>
  );
}
