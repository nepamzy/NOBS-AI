import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError, errorMessage } from "../api/client";
import type { Settings as SettingsData } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { DurationPicker } from "../components/DurationPicker";
import { LoadingState } from "../components/LoadingState";
import { StylePicker } from "../components/StylePicker";
import { VoicePicker } from "../components/VoicePicker";

export function Settings() {
  const { user } = useAuth();
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api
      .getSettings()
      .then(setSettings)
      .catch((err) => setError(errorMessage(err)));
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

  if (!settings) {
    return error ? (
      <p className="text-red-400">Couldn't load settings: {error}</p>
    ) : (
      <LoadingState />
    );
  }

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
          <StylePicker
            value={settings.default_style_preset}
            onChange={(id) => setSettings({ ...settings, default_style_preset: id })}
            compact
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

      <PasswordSection />
      {user?.role === "admin" && (
        <p className="mt-12 text-sm text-white/40">
          Spend tracking moved to its own{" "}
          <Link to="/spend" className="text-accent-400 hover:underline">
            Spend dashboard
          </Link>
          .
        </p>
      )}
    </div>
  );
}

function PasswordSection() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaved(false);

    if (newPassword !== confirmPassword) {
      setError("New password and confirmation don't match");
      return;
    }

    setSubmitting(true);
    try {
      await api.changePassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mt-12 max-w-md">
      <h2 className="font-heading text-lg font-semibold text-white">Change password</h2>
      <p className="mt-1 text-sm text-white/60">
        Changing your password signs you out everywhere else — this device stays logged in.
      </p>

      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-white/70">Current password</span>
          <input
            type="password"
            required
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-white"
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-white/70">New password</span>
          <input
            type="password"
            required
            minLength={8}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-white"
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-white/70">Confirm new password</span>
          <input
            type="password"
            required
            minLength={8}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
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
            disabled={submitting}
            className="w-fit rounded-md bg-accent-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-600 disabled:opacity-40"
          >
            {submitting ? "Updating…" : "Update password"}
          </button>
          {saved && <span className="text-xs text-emerald-400">Password updated</span>}
        </div>
      </form>
    </div>
  );
}

