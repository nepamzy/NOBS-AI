import { useEffect, useRef, useState } from "react";
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
  const [playingId, setPlayingId] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    api.listVoices().then(setPresets);
  }, []);

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
    };
  }, []);

  function togglePreview(preset: VoicePreset, e: React.MouseEvent) {
    e.stopPropagation();
    if (!preset.preview_path) return;

    if (playingId === preset.id) {
      audioRef.current?.pause();
      setPlayingId(null);
      return;
    }

    if (!audioRef.current) {
      audioRef.current = new Audio();
      audioRef.current.onended = () => setPlayingId(null);
    }
    audioRef.current.src = preset.preview_path;
    audioRef.current.play();
    setPlayingId(preset.id);
  }

  return (
    <div>
      <div className={`grid gap-2 ${compact ? "grid-cols-2" : "grid-cols-1 sm:grid-cols-2"}`}>
        {presets.map((preset) => {
          const selected = value === preset.id;
          const playing = playingId === preset.id;
          return (
            <div
              key={preset.id}
              role="button"
              tabIndex={0}
              onClick={() => onChange(preset.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") onChange(preset.id);
              }}
              className={`cursor-pointer rounded-md border p-3 text-left transition-colors ${
                selected
                  ? "border-accent-500 bg-accent-500/10"
                  : "border-white/10 bg-white/5 hover:border-white/20"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-white">{preset.name}</span>
                <div className="flex items-center gap-2">
                  {preset.preview_path && (
                    <button
                      type="button"
                      onClick={(e) => togglePreview(preset, e)}
                      className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-white/20 text-[10px] text-white/70 hover:border-accent-400 hover:text-accent-400"
                      aria-label={playing ? `Stop ${preset.name} preview` : `Play ${preset.name} preview`}
                    >
                      {playing ? "◼" : "▶"}
                    </button>
                  )}
                  {selected && <span className="text-xs text-accent-400">✓</span>}
                </div>
              </div>
              {!compact && <p className="mt-0.5 text-xs text-white/50">{preset.description}</p>}
            </div>
          );
        })}
      </div>
      <p className="mt-2 text-xs text-white/30">
        Preview clips are pre-recorded samples (ElevenLabs) so you can hear roughly what each
        voice sounds like — not what will actually narrate a video. Real generation still needs
        an engine configured and approved (Chatterbox or otherwise).
      </p>
    </div>
  );
}
