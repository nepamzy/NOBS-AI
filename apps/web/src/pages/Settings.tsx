import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { Settings as SettingsData } from "../api/types";

export function Settings() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getSettings().then(setSettings);
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!settings) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await api.updateSettings(settings);
      setSettings(updated);
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  if (!settings) return null;

  return (
    <div className="max-w-md">
      <h1 className="text-2xl font-semibold text-white">Settings</h1>
      <p className="mt-2 text-white/60">
        Defaults for new videos, and the weekly goal shown on the Dashboard. Provider settings
        (LLM, Wan, Chatterbox) live in <code className="text-white/80">.env</code>, not here —
        they're gated behind Nobert's cost approval per CLAUDE.md, not something to flip from the
        UI.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-5">
        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-white/70">Default duration (min)</span>
          <input
            type="number"
            min={1}
            max={20}
            value={settings.default_duration_minutes}
            onChange={(e) =>
              setSettings({ ...settings, default_duration_minutes: Number(e.target.value) })
            }
            className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-white"
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-white/70">Default voice</span>
          <input
            value={settings.default_voice_preset}
            onChange={(e) => setSettings({ ...settings, default_voice_preset: e.target.value })}
            placeholder="none"
            className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-white placeholder:text-white/30"
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-white/70">Default style</span>
          <input
            value={settings.default_style_preset}
            onChange={(e) => setSettings({ ...settings, default_style_preset: e.target.value })}
            placeholder="none"
            className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-white placeholder:text-white/30"
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-white/70">Weekly goal (videos)</span>
          <input
            type="number"
            min={1}
            max={20}
            value={settings.weekly_goal}
            onChange={(e) => setSettings({ ...settings, weekly_goal: Number(e.target.value) })}
            className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-white"
          />
        </label>

        {error && (
          <p className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {error}
          </p>
        )}

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={saving}
            className="w-fit rounded-md bg-white px-4 py-2 text-sm font-medium text-black disabled:opacity-40"
          >
            {saving ? "Saving…" : "Save"}
          </button>
          {saved && <span className="text-xs text-emerald-400">Saved</span>}
        </div>
      </form>
    </div>
  );
}
