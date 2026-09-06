import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { VoicePreset } from "../api/types";

export function VoicePicker({
  value,
  onChange,
  compact = false,
}: {
  value: string;
  onChange: (id: string) => void;
  compact?: boolean;
}) {
  const [presets, setPresets] = useState<VoicePreset[]>([]);

  useEffect(() => {
    api.listVoices().then(setPresets);
  }, []);

  return (
    <div>
      <div className={`grid gap-2 ${compact ? "grid-cols-2" : "grid-cols-1 sm:grid-cols-2"}`}>
        {presets.map((preset) => {
          const selected = value === preset.id;
          return (
            <button
              key={preset.id}
              type="button"
              onClick={() => onChange(preset.id)}
              className={`rounded-md border p-3 text-left transition-colors ${
                selected
                  ? "border-accent-500 bg-accent-500/10"
                  : "border-white/10 bg-white/5 hover:border-white/20"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-white">{preset.name}</span>
                {selected && <span className="text-xs text-accent-400">✓</span>}
              </div>
              {!compact && <p className="mt-0.5 text-xs text-white/50">{preset.description}</p>}
            </button>
          );
        })}
      </div>
      <p className="mt-2 text-xs text-white/30">
        No audio preview yet — nothing synthesizes until Chatterbox is configured and approved.
      </p>
    </div>
  );
}
