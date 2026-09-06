import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { CostCategory, Settings as SettingsData, SpendSummary } from "../api/types";
import { DurationPicker } from "../components/DurationPicker";
import { LoadingState } from "../components/LoadingState";
import { VoicePicker } from "../components/VoicePicker";

const CATEGORY_LABELS: Record<CostCategory, string> = {
  gpu: "GPU",
  llm: "LLM",
  tts: "TTS",
  video_generation: "Video Generation",
  storage: "Storage",
  database: "Database",
  hosting: "Hosting",
  networking: "Networking",
  domain: "Domain",
  other: "Other",
};

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

  if (!settings) return <LoadingState />;

  return (
    <div className="max-w-2xl">
      <h1 className="font-heading text-2xl font-semibold text-white">Settings</h1>
      <p className="mt-2 max-w-md text-white/60">
        Defaults for new videos, and the weekly goal shown on the Dashboard. Provider settings
        (LLM, Wan, Chatterbox) live in <code className="text-white/80">.env</code>, not here —
        they're gated behind Nobert's cost approval per CLAUDE.md, not something to flip from the
        UI.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 flex max-w-md flex-col gap-5">
        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-white/70">Default duration</span>
          <DurationPicker
            minutes={settings.default_duration_minutes}
            onChange={(minutes) => setSettings({ ...settings, default_duration_minutes: minutes })}
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-white/70">Default voice</span>
          <VoicePicker
            value={settings.default_voice_preset}
            onChange={(id) => setSettings({ ...settings, default_voice_preset: id })}
            compact
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
            className="w-fit rounded-md bg-accent-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-600 disabled:opacity-40"
          >
            {saving ? "Saving…" : "Save"}
          </button>
          {saved && <span className="text-xs text-emerald-400">Saved</span>}
        </div>
      </form>

      <SpendSection />
    </div>
  );
}

function SpendSection() {
  const [spend, setSpend] = useState<SpendSummary | null>(null);
  const [showForm, setShowForm] = useState(false);

  function refresh() {
    api.getSpend().then(setSpend);
  }

  useEffect(refresh, []);

  if (!spend) return null;

  return (
    <div className="mt-12">
      <h2 className="font-heading text-lg font-semibold text-white">Spend</h2>
      <p className="mt-1 text-sm text-white/60">
        Every paid action in this app is required to log here (CLAUDE.md Part 4) — estimated vs.
        actual, by category. Nothing paid has run yet, so this is honestly empty; log a cost
        manually below if you've spent something outside the app (e.g. a Runpod pod you started
        by hand).
      </p>

      <div className="mt-4 grid grid-cols-2 gap-4">
        <div className="rounded-lg border border-white/10 bg-white/5 p-4">
          <div className="text-xs uppercase tracking-wide text-white/50">Estimated</div>
          <div className="mt-1 text-2xl font-semibold text-white">
            ${spend.total_estimated_usd.toFixed(2)}
          </div>
        </div>
        <div className="rounded-lg border border-white/10 bg-white/5 p-4">
          <div className="text-xs uppercase tracking-wide text-white/50">Actual</div>
          <div className="mt-1 text-2xl font-semibold text-white">
            ${spend.total_actual_usd.toFixed(2)}
          </div>
        </div>
      </div>

      {spend.entries.length === 0 ? (
        <p className="mt-4 text-sm text-white/40">No spend recorded yet.</p>
      ) : (
        <ul className="mt-4 flex flex-col gap-2">
          {spend.entries.map((entry) => (
            <li
              key={entry.id}
              className="flex items-center justify-between rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm"
            >
              <div>
                <span className="font-medium text-white">{entry.service}</span>
                <span className="ml-2 text-xs text-white/40">
                  {CATEGORY_LABELS[entry.category]} · {entry.purpose}
                </span>
              </div>
              <div className="text-right text-xs text-white/50">
                {entry.actual_cost_usd != null
                  ? `$${entry.actual_cost_usd.toFixed(2)} actual`
                  : entry.estimated_cost_usd != null
                    ? `~$${entry.estimated_cost_usd.toFixed(2)} est.`
                    : "no cost logged"}
              </div>
            </li>
          ))}
        </ul>
      )}

      <button
        onClick={() => setShowForm((v) => !v)}
        className="mt-4 text-xs text-white/50 hover:text-white"
      >
        {showForm ? "Cancel" : "+ Log a cost manually"}
      </button>

      {showForm && (
        <SpendForm
          onLogged={() => {
            refresh();
            setShowForm(false);
          }}
        />
      )}
    </div>
  );
}

function SpendForm({ onLogged }: { onLogged: () => void }) {
  const [category, setCategory] = useState<CostCategory>("other");
  const [service, setService] = useState("");
  const [purpose, setPurpose] = useState("");
  const [actualCost, setActualCost] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.createSpendEntry({
        category,
        service,
        purpose,
        actual_cost_usd: actualCost ? Number(actualCost) : null,
      });
      onLogged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="mt-3 flex max-w-md flex-col gap-3 rounded-md border border-white/10 bg-white/5 p-4">
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs text-white/60">Category</span>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as CostCategory)}
            className="rounded-md border border-white/10 bg-black/20 px-2 py-1.5 text-sm text-white"
          >
            {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-white/60">Actual cost (USD)</span>
          <input
            type="number"
            step="0.01"
            min="0"
            value={actualCost}
            onChange={(e) => setActualCost(e.target.value)}
            placeholder="0.00"
            className="rounded-md border border-white/10 bg-black/20 px-2 py-1.5 text-sm text-white placeholder:text-white/30"
          />
        </label>
      </div>
      <label className="flex flex-col gap-1">
        <span className="text-xs text-white/60">Service</span>
        <input
          required
          value={service}
          onChange={(e) => setService(e.target.value)}
          placeholder="e.g. Runpod"
          className="rounded-md border border-white/10 bg-black/20 px-2 py-1.5 text-sm text-white placeholder:text-white/30"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-xs text-white/60">Purpose</span>
        <input
          required
          value={purpose}
          onChange={(e) => setPurpose(e.target.value)}
          placeholder="e.g. Test render for Project X"
          className="rounded-md border border-white/10 bg-black/20 px-2 py-1.5 text-sm text-white placeholder:text-white/30"
        />
      </label>
      {error && <p className="text-xs text-red-400">{error}</p>}
      <button
        type="submit"
        disabled={submitting}
        className="w-fit rounded-md bg-white px-3 py-1.5 text-xs font-medium text-black disabled:opacity-40"
      >
        {submitting ? "Logging…" : "Log cost"}
      </button>
    </form>
  );
}
