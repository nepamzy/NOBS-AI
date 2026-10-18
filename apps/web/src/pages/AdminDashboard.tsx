import { Plus, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../api/client";
import type { AdminUser, SignupPin, TokenPackage } from "../api/types";
import { LoadingState } from "../components/LoadingState";
import { Button, ErrorState, Panel, StatusPill } from "../components/ui";

type Tab = "users" | "pins" | "system";
const TABS: { key: Tab; label: string }[] = [
  { key: "users", label: "Users" },
  { key: "pins", label: "Invitation PINs" },
  { key: "system", label: "System" },
];

export function AdminDashboard() {
  const [tab, setTab] = useState<Tab>("users");
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
    <div className="max-w-4xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl font-semibold text-white">Admin Dashboard</h1>
          <p className="mt-1 max-w-lg text-white/60">
            Manage users and invitation PINs. Their projects and videos stay completely private
            from you — this is account control, not access to their content.
          </p>
        </div>
        <Button onClick={() => setTab("pins")}>
          <span className="inline-flex items-center gap-1.5">
            <Plus size={14} /> Invite User
          </span>
        </Button>
      </div>

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
        {tab === "users" && <UsersTab users={users} error={error} onChanged={refresh} />}
        {tab === "pins" && <PinsTab />}
        {tab === "system" && <SystemTab />}
      </div>
    </div>
  );
}

function UsersTab({
  users,
  error,
  onChanged,
}: {
  users: AdminUser[] | null;
  error: string | null;
  onChanged: () => void;
}) {
  const [search, setSearch] = useState("");

  const total = users?.length ?? 0;
  const active = users?.filter((u) => !u.is_suspended).length ?? 0;
  const suspended = users?.filter((u) => u.is_suspended).length ?? 0;

  const filtered = useMemo(() => {
    if (!users) return [];
    const q = search.trim().toLowerCase();
    if (!q) return users;
    return users.filter(
      (u) => u.display_name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q),
    );
  }, [users, search]);

  return (
    <div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Metric label="Total Users" value={total} />
        <Metric label="Active Users" value={active} />
        <Metric label="Suspended" value={suspended} />
      </div>

      <div className="relative mt-6 max-w-sm">
        <Search size={14} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-white/40" />
        <label className="sr-only" htmlFor="admin-user-search">
          Search users
        </label>
        <input
          id="admin-user-search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search users…"
          className="w-full rounded-full border border-white/10 bg-white/5 py-1.5 pr-3 pl-8 text-sm text-white placeholder:text-white/30"
        />
      </div>

      {error && (
        <div className="mt-4">
          <ErrorState message={error} />
        </div>
      )}

      {users === null ? (
        <div className="mt-6">
          <LoadingState />
        </div>
      ) : filtered.length === 0 ? (
        <p className="mt-6 text-sm text-white/40">
          {search ? "No users match your search." : "No one has signed up yet."}
        </p>
      ) : (
        <Panel className="mt-6 overflow-x-auto p-0">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-white/10 text-xs uppercase tracking-wide text-white/40">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Email</th>
                <th className="px-4 py-3 font-medium">Role</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((user) => (
                <UserRow key={user.id} user={user} onChanged={onChanged} />
              ))}
            </tbody>
          </table>
        </Panel>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <Panel>
      <div className="text-xs uppercase tracking-wide text-white/50">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-white">{value}</div>
    </Panel>
  );
}

function UserRow({ user, onChanged }: { user: AdminUser; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState(false);
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
    <>
      <tr className="border-b border-white/5 last:border-0">
        <td className="px-4 py-3 text-white">{user.display_name}</td>
        <td className="px-4 py-3 text-white/60">{user.email}</td>
        <td className="px-4 py-3">
          <StatusPill tone={user.role === "admin" ? "info" : "neutral"} label={user.role === "admin" ? "Admin" : "Guest"} />
        </td>
        <td className="px-4 py-3">
          <StatusPill tone={user.is_suspended ? "error" : "success"} label={user.is_suspended ? "Suspended" : "Active"} />
        </td>
        <td className="px-4 py-3">
          <button
            onClick={() => setExpanded((v) => !v)}
            className="rounded-md px-2 py-1 text-white/50 hover:bg-white/5 hover:text-white"
            aria-expanded={expanded}
            aria-label={`Actions for ${user.display_name}`}
          >
            {expanded ? "×" : "⋯"}
          </button>
        </td>
      </tr>
      {expanded && (
        <tr className="border-b border-white/5 bg-white/[0.02] last:border-0">
          <td colSpan={5} className="px-4 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-white/50">{user.token_balance} tokens</span>
              {user.is_suspended ? (
                <Button variant="secondary" size="sm" onClick={() => run(() => api.unsuspendUser(user.id))} disabled={busy}>
                  Unsuspend
                </Button>
              ) : (
                <Button variant="secondary" size="sm" onClick={() => run(() => api.suspendUser(user.id))} disabled={busy}>
                  Suspend
                </Button>
              )}
              <Button
                variant="danger"
                size="sm"
                onClick={() => {
                  if (confirm(`Delete ${user.display_name}? This deletes their projects and videos.`)) {
                    run(() => api.deleteUser(user.id));
                  }
                }}
                disabled={busy}
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
                  size="sm"
                  onClick={() => run(() => api.grantTokens(user.id, Number(grantAmount)))}
                  disabled={busy || !Number(grantAmount)}
                >
                  Grant tokens
                </Button>
              </div>
            </div>
            {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
          </td>
        </tr>
      )}
    </>
  );
}

function PinsTab() {
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
    <Panel>
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

      <p className="mt-4 text-xs text-white/40">
        There's no history list here — the backend only generates a PIN, it doesn't store or list
        past ones, so a previously issued PIN can't be shown again once you navigate away.
      </p>
    </Panel>
  );
}

function SystemTab() {
  const [status, setStatus] = useState<"checking" | "ok" | "error">("checking");
  const [detail, setDetail] = useState<string | null>(null);

  function fetchHealth() {
    api
      .health()
      .then((res) => {
        setStatus(res.status === "ok" ? "ok" : "error");
        setDetail(res.status === "ok" ? null : res.status);
      })
      .catch((err) => {
        setStatus("error");
        setDetail(err instanceof ApiError ? err.message : String(err));
      });
  }

  useEffect(fetchHealth, []);

  function check() {
    setStatus("checking");
    setDetail(null);
    fetchHealth();
  }

  return (
    <div className="flex flex-col gap-4">
      <Panel className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm text-white">API server</p>
          <p className="text-xs text-white/40">
            Live <code className="text-white/60">GET /health</code> check — not cached.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {status === "checking" && <StatusPill tone="neutral" label="Checking…" />}
          {status === "ok" && <StatusPill tone="success" label="Reachable" />}
          {status === "error" && <StatusPill tone="error" label="Unreachable" />}
          <Button variant="secondary" size="sm" onClick={check}>
            Re-check
          </Button>
        </div>
      </Panel>
      {detail && (
        <div className="-mt-2">
          <ErrorState message={detail} />
        </div>
      )}

      <PackagesPreview />

      <Panel>
        <p className="text-sm text-white">Database, queue, and storage</p>
        <p className="mt-1 text-xs text-white/40">
          No dedicated status endpoints exist for Postgres, Redis, or the job queue yet — the
          health check above only confirms the API process itself is up and responding.
        </p>
      </Panel>
    </div>
  );
}

function PackagesPreview() {
  const [packages, setPackages] = useState<TokenPackage[] | null>(null);

  useEffect(() => {
    api.listPackages().then(setPackages).catch(() => setPackages([]));
  }, []);

  if (!packages || packages.length === 0) return null;

  return (
    <Panel>
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
