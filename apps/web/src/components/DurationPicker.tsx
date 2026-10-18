import { useState } from "react";

// Video length in seconds. Short options are for quick tests and clips.
export const CREATE_DURATION_PRESETS = [5, 10, 15, 30, 60, 180, 300, 600, 900];
export const MINUTE_DURATION_PRESETS = [60, 180, 300, 600, 900];

function label(seconds: number): string {
  if (seconds < 60) return `${seconds} sec`;
  return `${seconds / 60} min`;
}

export function DurationPicker({
  seconds,
  onChange,
  presets = CREATE_DURATION_PRESETS,
}: {
  seconds: number;
  onChange: (seconds: number) => void;
  presets?: number[];
}) {
  const [customOpen, setCustomOpen] = useState(!presets.includes(seconds));

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {presets.map((preset) => {
          const selected = !customOpen && seconds === preset;
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
              {label(preset)}
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
        <label className="mt-2 flex items-center gap-2 text-sm text-white/60">
          <input
            type="number"
            min={5}
            max={3600}
            autoFocus
            value={seconds}
            onChange={(e) => onChange(Number(e.target.value))}
            className="w-32 rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-white"
          />
          seconds
        </label>
      )}
    </div>
  );
}
