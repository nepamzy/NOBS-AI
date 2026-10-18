import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { AdminUser, SignupPin, TokenPackage } from "../api/types";
import { LoadingState } from "../components/LoadingState";
import { Button, ErrorState, Panel, StatusPill } from "../components/ui";

export function AdminDashboard() {
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    api
      .listUsers()
      .then(setUsers)
      .catch((err) => setError(err instanceof ApiError ? err.message : String(err)));
  }

  useEffect(refresh, []);

  return (
    <div className="max-w-3xl">
      <h1 className="font-heading text-2xl font-semibold text-white">Admin</h1>
      <p className="mt-1 text-white/60">
        Invite people with a one-time PIN, and manage everyone who's signed up. Their projects and
        videos are completely separate from yours — this is account control, not access to their
        content.
      </p>

      <PinGenerator />

      <PackagesPreview />

      <h2 className="mt-10 mb-3 text-sm font-medium uppercase tracking-wide text-white/50">
        Users
      </h2>
      {error && <ErrorState message={error} />}
      {users === null ? (
        <LoadingState />
      ) : users.length === 0 ? (
        <p className="text-sm text-white/40">No one has signed up yet.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {users.map((user) => (
            <UserRow key={user.id} user={user} onChanged={refresh} />
          ))}
        </ul>
      )}
    </div>
  );
}

function PinGenerator() {
  const [pin, setPin] = useState<SignupPin | null>(null);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!pin) return;
    const tick = () => {
      const remaining = Math.max(
        0,
        Math.round((new Date(pin.expires_at).getTime() - Date.now()) / 1000),
      );
      setSecondsLeft(remaining);
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [pin]);

  async function generate() {
    setGenerating(true);
    setError(null);
    try {
      setPin(await api.generatePin());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setGenerating(false);
    }
  }

  const expired = pin !== null && secondsLeft <= 0;

  return (
    <Panel className="mt-6">
      <h2 className="font-heading text-base font-semibold text-white">Invite someone</h2>
      <p className="mt-1 text-sm text-white/60">
        Generates a 6-digit PIN, good for 5 minutes and exactly one signup. Send it to them
        yourself — it's shown here only once.
      </p>

      <Button onClick={generate} disabled={generating} className="mt-4">
        {generating ? "Generating…" : "Generate PIN"}
      </Button>

      {error && (
        <div className="mt-3">
          <ErrorState message={error} />
        </div>
      )}

      {pin && (
        <div className="mt-4 flex items-center gap-4 rounded-md border border-accent-500/30 bg-accent-500/10 px-4 py-3">
          <span className="font-mono text-2xl tracking-[0.3em] text-white">
            {expired ? "——————" : pin.code}
          </span>
          <span className={`text-xs ${expired ? "text-red-400" : "text-white/50"}`}>
            {expired ? "Expired" : `Expires in ${secondsLeft}s`}
          </span>
        </div>
      )}
    </Panel>
  );
}

function PackagesPreview() {
  const [packages, setPackages] = useState<TokenPackage[] | null>(null);

  useEffect(() => {
    api.listPackages().then(setPackages).catch(() => setPackages([]));
  }, []);

  if (!packages || packages.length === 0) return null;

  return (
    <Panel className="mt-6">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-heading text-base font-semibold text-white">Token packages (draft)</h2>
        <StatusPill tone="neutral" label="Not purchasable" />
      </div>
      <p className="mt-1 text-sm text-white/60">
        Placeholder pricing only — no payment provider is connected. Adjust these anytime in{" "}
        <code className="text-white/80">services/payments/packages.py</code>.
      </p>
      <div className="mt-4 grid grid-cols-3 gap-3">
        {packages.map((pkg) => (
          <div key={pkg.id} className="rounded-md border border-white/10 bg-black/20 p-3">
            <div className="text-sm font-medium text-white">{pkg.name}</div>
            <div className="mt-1 text-xs text-white/50">{pkg.tokens} tokens</div>
            <div className="mt-2 text-lg font-semibold text-accent-400">
              ${pkg.price_usd.toFixed(2)}
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function UserRow({ user, onChanged }: { user: AdminUser; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const [grantAmount, setGrantAmount] = useState("5");
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <li>
      <Panel className="px-4 py-3 text-sm">
        <div className="flex items-center justify-between gap-3">
          <div>
            <span className="font-medium text-white">{user.display_name}</span>
            <span className="ml-2 text-xs text-white/40">{user.email}</span>
            {user.is_suspended && (
              <span className="ml-2">
                <StatusPill tone="error" label="Suspended" />
              </span>
            )}
          </div>
          <span className="text-xs text-white/50">{user.token_balance} tokens</span>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          {user.is_suspended ? (
            <Button
              variant="secondary"
              onClick={() => run(() => api.unsuspendUser(user.id))}
              disabled={busy}
              size="sm"
            >
              Unsuspend
            </Button>
          ) : (
            <Button
              variant="secondary"
              onClick={() => run(() => api.suspendUser(user.id))}
              disabled={busy}
              size="sm"
            >
              Suspend
            </Button>
          )}
          <Button
            variant="danger"
            onClick={() => {
              if (confirm(`Delete ${user.display_name}? This deletes their projects and videos.`)) {
                run(() => api.deleteUser(user.id));
              }
            }}
            disabled={busy}
            size="sm"
          >
            Delete
          </Button>
          <div className="ml-auto flex items-center gap-1.5">
            <input
              type="number"
              min={1}
              value={grantAmount}
              onChange={(e) => setGrantAmount(e.target.value)}
              className="w-16 rounded-md border border-white/10 bg-black/20 px-2 py-1 text-xs text-white"
            />
            <Button
              variant="secondary"
              onClick={() => run(() => api.grantTokens(user.id, Number(grantAmount)))}
              disabled={busy || !Number(grantAmount)}
              size="sm"
            >
              Grant tokens
            </Button>
          </div>
        </div>

        {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
      </Panel>
    </li>
  );
}
