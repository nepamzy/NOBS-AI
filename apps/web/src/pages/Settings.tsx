import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError, errorMessage } from "../api/client";
import type { ProviderStatus, Settings as SettingsData } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { DurationPicker } from "../components/DurationPicker";
import { LoadingState } from "../components/LoadingState";
import { StylePicker } from "../components/StylePicker";
import { Button, ErrorState, Panel, StatusPill } from "../components/ui";
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
      <ErrorState message={`Couldn't load settings: ${error}`} />
    ) : (
      <LoadingState />
    );
  }

  return (
    <div className="max-w-2xl">
      <h1 className="font-heading text-2xl font-semibold text-white">Settings</h1>
      <p className="mt-2 max-w-md text-white/60">
        Defaults for new videos, and the weekly goal shown on the Dashboard.
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

        {error && <ErrorState message={error} />}

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </Button>
          {saved && <span className="text-xs text-emerald-400">Saved</span>}
        </div>
      </form>

      <PasswordSection />
      {user?.role === "admin" && <ProviderStatusSection />}
    </div>
  );
}

function ProviderStatusSection() {
  const [providers, setProviders] = useState<ProviderStatus[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getConnectionsStatus()
      .then((s) => setProviders(s.providers))
      .catch((err) => setError(errorMessage(err)));
  }, []);

  return (
    <div className="mt-12 max-w-md">
      <h2 className="font-heading text-lg font-semibold text-white">Provider status</h2>
      <p className="mt-1 text-sm text-white/60">
        Whether each engine's required configuration is present — never the values themselves.
        Set and change these directly in your deployment's environment config, not here; see{" "}
        <code className="text-white/80">.env.example</code> for what each one needs.
      </p>

      {error && (
        <div className="mt-3">
          <ErrorState message={error} />
        </div>
      )}
      {!providers && !error && (
        <div className="mt-3">
          <LoadingState />
        </div>
      )}
      {providers && (
        <ul className="mt-3 flex flex-col gap-2">
          {providers.map((p) => (
            <li key={p.id}>
              <Panel className="flex items-center justify-between gap-3 py-2.5">
                <div>
                  <p className="text-sm text-white">{p.name}</p>
                  <p className="text-xs text-white/40">{p.detail}</p>
                </div>
                <StatusPill
                  tone={p.configured ? "success" : "neutral"}
                  label={p.configured ? "Configured" : "Not configured"}
                />
              </Panel>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-3 text-xs text-white/40">
        YouTube channel connections live on their own{" "}
        <Link to="/connections" className="text-accent-400 hover:underline">
          Channel Connections page
        </Link>
        , where the state is checked live rather than just inferred from config presence.
      </p>
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

        {error && <ErrorState message={error} />}

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={submitting}>
            {submitting ? "Updating…" : "Update password"}
          </Button>
          {saved && <span className="text-xs text-emerald-400">Password updated</span>}
        </div>
      </form>
    </div>
  );
}
