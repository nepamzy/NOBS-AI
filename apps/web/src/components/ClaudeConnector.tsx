import { Check, Copy, Plug } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, connectorUrl, errorMessage } from "../api/client";
import type { ConnectorKey } from "../api/types";
import { Button, ErrorState, Panel, StatusPill } from "./ui";

/** Admin-only. Creates the secret link that connects a Claude session to
 * NOBS AI (Claude → Settings → Connectors → Add custom connector). The link
 * is shown exactly once; only a hash is stored server-side. */
export function ClaudeConnector() {
  const [keys, setKeys] = useState<ConnectorKey[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [fresh, setFresh] = useState<{ id: string; url: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const load = useCallback(() => {
    api
      .listConnectorKeys()
      .then((list) => {
        setKeys(list);
        setError(null);
      })
      .catch((err) => setError(errorMessage(err)));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate() {
    setBusy(true);
    setCopied(false);
    try {
      const created = await api.createConnectorKey("Claude");
      setFresh({ id: created.id, url: connectorUrl(created.key) });
      load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleRevoke(key: ConnectorKey) {
    if (!window.confirm(`Revoke "${key.name}" (${key.key_prefix}…)? Any Claude session using it stops working immediately.`)) {
      return;
    }
    try {
      await api.revokeConnectorKey(key.id);
      if (fresh?.id === key.id) setFresh(null);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleCopy() {
    if (!fresh) return;
    try {
      await navigator.clipboard.writeText(fresh.url);
      setCopied(true);
    } catch {
      setError("Couldn't copy automatically — select the link and copy it by hand.");
    }
  }

  const active = (keys ?? []).filter((k) => !k.revoked);

  return (
    <Panel>
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent-500/20">
          <Plug size={18} className="text-accent-400" />
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="font-heading text-base font-semibold text-white">Claude connector</h3>
          <p className="mt-1 text-sm text-white/60">
            Lets a Claude session hand a finished video to NOBS AI, or produce one you approved
            here. Finished videos wait for your review. Claude only publishes or schedules when
            you tell it to, for that exact video; it can't delete anything or spend money.
          </p>
        </div>
        <Button onClick={handleCreate} disabled={busy}>
          {busy ? "Creating…" : "New connector link"}
        </Button>
      </div>

      {error && (
        <div className="mt-3">
          <ErrorState message={error} />
        </div>
      )}

      {fresh && (
        <div className="mt-4 rounded-md border border-amber-400/30 bg-amber-400/5 p-3">
          <p className="text-sm font-medium text-amber-200">
            Copy this link now — it won't be shown again.
          </p>
          <div className="mt-2 flex items-center gap-2">
            <input
              readOnly
              value={fresh.url}
              onFocus={(e) => e.currentTarget.select()}
              className="min-w-0 flex-1 rounded-md border border-white/10 bg-black/30 px-3 py-2 font-mono text-xs text-white/80"
            />
            <Button variant="secondary" onClick={handleCopy}>
              <span className="inline-flex items-center gap-1.5">
                {copied ? <Check size={14} /> : <Copy size={14} />}
                {copied ? "Copied" : "Copy"}
              </span>
            </Button>
          </div>
          <p className="mt-2 text-xs text-white/50">
            In Claude: Settings → Connectors → Add custom connector → paste this link. Treat it
            like a password — anyone with it can add videos to your account.
          </p>
        </div>
      )}

      {active.length > 0 && (
        <ul className="mt-4 divide-y divide-white/5 rounded-md border border-white/10">
          {active.map((k) => (
            <li key={k.id} className="flex items-center justify-between gap-3 px-3 py-2.5 text-sm">
              <div className="min-w-0">
                <span className="font-mono text-white/80">{k.key_prefix}…</span>
                <span className="ml-2 text-white/40">
                  {k.last_used_at
                    ? `last used ${new Date(k.last_used_at).toLocaleString()}`
                    : "never used"}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <StatusPill tone="success" label="Active" />
                <Button variant="secondary" size="sm" onClick={() => handleRevoke(k)}>
                  Revoke
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
