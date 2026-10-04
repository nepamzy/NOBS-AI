import { useEffect, useState } from "react";
import { api, ApiError, errorMessage } from "../api/client";
import type { BillingType, CostCategory, CostEntry, CostStatus, SpendSummary } from "../api/types";
import { LoadingState } from "../components/LoadingState";

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

const BILLING_LABELS: Record<BillingType, string> = {
  hourly: "Hourly",
  per_request: "Per request",
  per_token: "Per token",
  monthly: "Monthly",
  usage_based: "Usage-based",
  one_time: "One-time",
  free: "Free",
};

const STATUS_STYLES: Record<CostStatus, { dot: string; text: string; label: string }> = {
  active: { dot: "bg-emerald-400", text: "text-emerald-300", label: "Active" },
  pending: { dot: "bg-amber-400", text: "text-amber-300", label: "Pending" },
  stopped: { dot: "bg-white/30", text: "text-white/50", label: "Stopped" },
};

function effectiveCost(entry: CostEntry): number {
  return entry.actual_cost_usd ?? entry.estimated_cost_usd ?? 0;
}

export function SpendDashboard() {
  const [spend, setSpend] = useState<SpendSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  function refresh() {
    api
      .getSpend()
      .then(setSpend)
      .catch((err) => setError(errorMessage(err)));
  }

  useEffect(refresh, []);

  async function cycleStatus(entry: CostEntry) {
    const next: Record<CostStatus, CostStatus> = {
      active: "stopped",
      stopped: "pending",
      pending: "active",
    };
    setBusyId(entry.id);
    try {
      await api.updateSpendEntry(entry.id, { status: next[entry.status] });
      refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  async function remove(entry: CostEntry) {
    if (!confirm(`Remove "${entry.service}" from the tracker? This doesn't cancel it anywhere — it only stops tracking it here.`)) {
      return;
    }
    setBusyId(entry.id);
    try {
      await api.deleteSpendEntry(entry.id);
      refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  if (error && !spend) {
    return <p className="p-6 text-sm text-red-400">{error}</p>;
  }
  if (!spend) {
    return (
      <div className="p-6">
        <LoadingState />
      </div>
    );
  }

  const breakdown = [...spend.by_category]
    .map((b) => ({ ...b, total: b.actual_usd || b.estimated_usd }))
    .filter((b) => b.total > 0)
    .sort((a, b) => b.total - a.total);
  const maxTotal = Math.max(...breakdown.map((b) => b.total), 1);

  const sortedEntries = [...spend.entries].sort((a, b) => {
    const order: Record<CostStatus, number> = { active: 0, pending: 1, stopped: 2 };
    if (order[a.status] !== order[b.status]) return order[a.status] - order[b.status];
    return effectiveCost(b) - effectiveCost(a);
  });

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="font-heading text-2xl font-semibold text-white">Spend</h1>
      <p className="mt-1 text-sm text-white/60">
        Every real-money cost across this project — cloud GPU, hosting, APIs — in one place.
      </p>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Active monthly" value={`$${spend.active_monthly_recurring_usd.toFixed(2)}`} />
        <StatTile label="Total estimated" value={`$${spend.total_estimated_usd.toFixed(2)}`} />
        <StatTile label="Total actual" value={`$${spend.total_actual_usd.toFixed(2)}`} />
        <StatTile label="Active · Pending" value={`${spend.active_count} · ${spend.pending_count}`} />
      </div>

      {breakdown.length > 0 && (
        <div className="mt-8">
          <h2 className="font-heading text-sm font-semibold uppercase tracking-wide text-white/50">
            By category
          </h2>
          <div className="mt-3 flex flex-col gap-2">
            {breakdown.map((b) => (
              <div key={b.category} className="flex items-center gap-3">
                <span className="w-32 shrink-0 truncate text-sm text-white/70">
                  {CATEGORY_LABELS[b.category]}
                </span>
                <div className="h-5 flex-1 rounded-sm bg-white/5">
                  <div
                    className="h-full rounded-sm bg-accent-500"
                    style={{ width: `${Math.max((b.total / maxTotal) * 100, 3)}%` }}
                  />
                </div>
                <span className="w-16 shrink-0 text-right text-sm text-white/80">
                  ${b.total.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-8">
        <div className="flex items-center justify-between">
          <h2 className="font-heading text-sm font-semibold uppercase tracking-wide text-white/50">
            All services
          </h2>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="text-xs text-white/50 hover:text-white"
          >
            {showForm ? "Cancel" : "+ Log a cost manually"}
          </button>
        </div>

        {showForm && <SpendForm onLogged={() => { refresh(); setShowForm(false); }} />}

        {error && <p className="mt-3 text-xs text-red-400">{error}</p>}

        <ul className="mt-4 flex flex-col gap-2">
          {sortedEntries.map((entry) => {
            const style = STATUS_STYLES[entry.status];
            return (
              <li
                key={entry.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-white/10 bg-white/5 px-3 py-2.5 text-sm"
              >
                <div className="flex min-w-0 items-center gap-2">
                  <span className={`h-2 w-2 shrink-0 rounded-full ${style.dot}`} title={style.label} />
                  <div className="min-w-0">
                    <div className="truncate font-medium text-white">{entry.service}</div>
                    <div className="truncate text-xs text-white/40">
                      {CATEGORY_LABELS[entry.category]}
                      {entry.billing_type && ` · ${BILLING_LABELS[entry.billing_type]}`}
                      {" · "}
                      {entry.purpose}
                    </div>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className={`text-xs ${style.text}`}>{style.label}</span>
                  <span className="text-right text-xs text-white/60">
                    {entry.actual_cost_usd != null
                      ? `$${entry.actual_cost_usd.toFixed(2)} actual`
                      : entry.estimated_cost_usd != null
                        ? `~$${entry.estimated_cost_usd.toFixed(2)} est.`
                        : "no cost logged"}
                  </span>
                  <button
                    disabled={busyId === entry.id}
                    onClick={() => cycleStatus(entry)}
                    className="text-xs text-white/40 hover:text-white disabled:opacity-40"
                    title="Cycle status (active → stopped → pending → active)"
                  >
                    Change status
                  </button>
                  <button
                    disabled={busyId === entry.id}
                    onClick={() => remove(entry)}
                    className="text-xs text-white/40 hover:text-red-400 disabled:opacity-40"
                  >
                    Remove
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 p-4">
      <div className="text-xs uppercase tracking-wide text-white/50">{label}</div>
      <div className="mt-1 text-xl font-semibold text-white">{value}</div>
    </div>
  );
}

function SpendForm({ onLogged }: { onLogged: () => void }) {
  const [category, setCategory] = useState<CostCategory>("other");
  const [status, setStatus] = useState<CostStatus>("active");
  const [billingType, setBillingType] = useState<BillingType | "">("");
  const [service, setService] = useState("");
  const [purpose, setPurpose] = useState("");
  const [actualCost, setActualCost] = useState("");
  const [estimatedCost, setEstimatedCost] = useState("");
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
        status,
        billing_type: billingType || null,
        actual_cost_usd: actualCost ? Number(actualCost) : null,
        estimated_cost_usd: estimatedCost ? Number(estimatedCost) : null,
      });
      onLogged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="mt-3 flex max-w-md flex-col gap-3 rounded-md border border-white/10 bg-white/5 p-4"
    >
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
          <span className="text-xs text-white/60">Status</span>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as CostStatus)}
            className="rounded-md border border-white/10 bg-black/20 px-2 py-1.5 text-sm text-white"
          >
            <option value="active">Active</option>
            <option value="pending">Pending</option>
            <option value="stopped">Stopped</option>
          </select>
        </label>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs text-white/60">Billing type</span>
          <select
            value={billingType}
            onChange={(e) => setBillingType(e.target.value as BillingType | "")}
            className="rounded-md border border-white/10 bg-black/20 px-2 py-1.5 text-sm text-white"
          >
            <option value="">Unspecified</option>
            {Object.entries(BILLING_LABELS).map(([value, label]) => (
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
        <span className="text-xs text-white/60">Estimated cost (USD) — if actual isn't known yet</span>
        <input
          type="number"
          step="0.01"
          min="0"
          value={estimatedCost}
          onChange={(e) => setEstimatedCost(e.target.value)}
          placeholder="0.00"
          className="rounded-md border border-white/10 bg-black/20 px-2 py-1.5 text-sm text-white placeholder:text-white/30"
        />
      </label>
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
