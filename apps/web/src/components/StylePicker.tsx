import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { StylePreset } from "../api/types";

export function StylePicker({
  value,
  onChange,
  compact = false,
}: {
  value: string;
  onChange: (id: string) => void;
  compact?: boolean;
}) {
  const [presets, setPresets] = useState<StylePreset[]>([]);

  useEffect(() => {
    api.listStyles().then(setPresets);
  }, []);

  return (
    <div className={`grid gap-2 ${compact ? "grid-cols-2" : "grid-cols-1 sm:grid-cols-2"}`}>
      {presets.map((preset) => {
        const selected = value === preset.id;
        return (
          <button
            key={preset.id}
            type="button"
            onClick={() => onChange(preset.id)}
            className={`flex items-start gap-2.5 rounded-md border p-3 text-left transition-colors ${
              selected
                ? "border-accent-500 bg-accent-500/10"
                : "border-white/10 bg-white/5 hover:border-white/20"
            }`}
          >
            <span
              className="mt-0.5 h-3 w-3 shrink-0 rounded-full"
              style={{ backgroundColor: preset.accent_hex }}
            />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-white">{preset.name}</span>
                {selected && <span className="text-xs text-accent-400">✓</span>}
              </div>
              {!compact && <p className="mt-0.5 text-xs text-white/50">{preset.description}</p>}
            </div>
          </button>
        );
      })}
    </div>
  );
}
