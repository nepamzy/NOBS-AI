import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError, errorMessage } from "../api/client";
import type { ConnectionTestResult, ProviderStatus, Settings as SettingsData } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { DurationPicker, MINUTE_DURATION_PRESETS } from "../components/DurationPicker";
import { LoadingState } from "../components/LoadingState";
import { StylePicker } from "../components/StylePicker";
import { Button, ErrorState, Panel, StatusPill } from "../components/ui";
import { VoicePicker } from "../components/VoicePicker";

type Tab = "profile" | "notifications" | "preferences" | "security";
const TABS: { key: Tab; label: string }[] = [
  { key: "profile", label: "Profile" },
  { key: "notifications", label: "Notifications" },
  { key: "preferences", label: "Preferences" },
  { key: "security", label: "Security" },
];

export function Settings() {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>("profile");

  return (
    <div className="max-w-2xl">
      <h1 className="font-heading text-2xl font-semibold text-white">Settings</h1>
      <p className="mt-2 max-w-md text-white/60">Manage your account and preferences.</p>

      <div className="mt-6 flex flex-wrap gap-1 rounded-lg border border-white/10 bg-white/5 p-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === t.key ? "bg-accent-500/20 text-accent-300" : "text-white/50 hover:text-white"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === "profile" && <ProfileTab />}
        {tab === "notifications" && <NotificationsTab />}
        {tab === "preferences" && <PreferencesTab />}
        {tab === "security" && <SecurityTab />}
      </div>

      {user?.role === "admin" && <ProviderStatusSection />}
    </div>
  );
}

function ProfileTab() {
  const { user } = useAuth();
  if (!user) return <LoadingState />;

  return (
    <Panel>
      <div className="flex items-start gap-4">
        <span className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-accent-400 to-accent-600 text-xl font-bold text-white">
          {user.display_name.slice(0, 1).toUpperCase()}
        </span>
        <dl className="flex-1 flex-col gap-3 text-sm">
          <Row label="Name" value={user.display_name} />
          <Row label="Email" value={user.email} />
          <Row label="Role" value={user.role === "admin" ? "Admin" : "Guest"} />
          {user.role !== "admin" && <Row label="Token balance" value={String(user.token_balance)} />}
        </dl>
      </div>
      <p className="mt-4 text-xs text-white/40">
        Read-only — there's no endpoint to change your name, email, avatar, timezone, or language
        from here yet. Only your password can actually be changed (Security tab).
      </p>
    </Panel>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-white/5 py-2 first:pt-0">
      <dt className="text-white/50">{label}</dt>
      <dd className="text-right text-white">{value}</dd>
    </div>
  );
}

function NotificationsTab() {
  return (
    <Panel>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-white">Email and push notification preferences</p>
        <StatusPill tone="neutral" label="Not available" />
      </div>
      <p className="mt-1 text-xs text-white/40">
        There's no notification system in this app yet — the bell in the top bar is computed live
        from your actual videos/clips each time you load a page, not a subscribable feed with its
        own preferences.
      </p>
    </Panel>
  );
}

function PreferencesTab() {
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
    return error ? <ErrorState message={`Couldn't load settings: ${error}`} /> : <LoadingState />;
  }

  return (
    <Panel>
      <p className="text-sm text-white/60">Defaults for new videos, and the weekly goal shown on the Dashboard.</p>
      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-5">
        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-white/70">Default duration</span>
          <DurationPicker
            seconds={settings.default_duration_minutes * 60}
            presets={MINUTE_DURATION_PRESETS}
            onChange={(seconds) =>
              setSettings({ ...settings, default_duration_minutes: Math.max(1, Math.round(seconds / 60)) })
            }
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
            className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-white"
          />
        </label>

        {error && <ErrorState message={error} />}

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save Changes"}
          </Button>
          {saved && <span className="text-xs text-emerald-400">Saved</span>}
        </div>
      </form>
    </Panel>
  );
}

function SecurityTab() {
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
    <Panel>
      <h2 className="font-heading text-base font-semibold text-white">Change password</h2>
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
            className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-white"
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
            className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-white"
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
            className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-white"
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
    </Panel>
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
    <div className="mt-8">
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
              <ProviderRow provider={p} />
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

function ProviderRow({ provider }: { provider: ProviderStatus }) {
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<ConnectionTestResult | null>(null);

  function handleTest() {
    setTesting(true);
    setResult(null);
    api
      .testConnection(provider.id)
      .then(setResult)
      .catch((err) => setResult({ id: provider.id, ok: false, detail: errorMessage(err) }))
      .finally(() => setTesting(false));
  }

  return (
    <Panel className="py-2.5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm text-white">{provider.name}</p>
          <p className="text-xs text-white/40">{provider.detail}</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusPill
            tone={provider.configured ? "success" : "neutral"}
            label={provider.configured ? "Configured" : "Not configured"}
          />
          {provider.configured && (
            <Button variant="secondary" onClick={handleTest} disabled={testing}>
              {testing ? "Testing…" : "Test"}
            </Button>
          )}
        </div>
      </div>
      {result && (
        <p className={`mt-2 text-xs ${result.ok ? "text-emerald-300" : "text-amber-300"}`}>
          {result.ok ? "Working: " : "Not working: "}
          {result.detail}
        </p>
      )}
    </Panel>
  );
}
