import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import type { ChannelConnectionStatus } from "../api/types";
import { LoadingState } from "../components/LoadingState";
import { Button, ErrorState, Panel, StatusPill, type Tone } from "../components/ui";

function channelTone(channel: ChannelConnectionStatus): { tone: Tone; label: string } {
  if (!channel.configured) return { tone: "neutral", label: "Not configured" };
  if (channel.connected === true) return { tone: "success", label: "Connected" };
  if (channel.connected === false) return { tone: "error", label: "Connection failed" };
  return { tone: "neutral", label: "Not checked" };
}

export function ChannelConnections() {
  const [status, setStatus] = useState<{
    providers: unknown;
    youtube_channels: ChannelConnectionStatus[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  const load = useCallback(() => {
    return api
      .getConnectionsStatus()
      .then((s) => {
        setStatus(s);
        setError(null);
      })
      .catch((err) => setError(errorMessage(err)));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function handleRecheck() {
    setChecking(true);
    load().finally(() => setChecking(false));
  }

  if (error) return <ErrorState message={`Couldn't load connection status: ${error}`} />;
  if (!status) return <LoadingState />;

  return (
    <div className="max-w-2xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl font-semibold text-white">Channel Connections</h1>
          <p className="mt-1 text-white/60">
            Real YouTube OAuth state — checked live against YouTube just now, not inferred from a
            button click.
          </p>
        </div>
        <Button variant="secondary" onClick={handleRecheck} disabled={checking}>
          {checking ? "Checking…" : "Re-check"}
        </Button>
      </div>

      <div className="mt-6 flex flex-col gap-4">
        {status.youtube_channels.map((channel) => {
          const { tone, label } = channelTone(channel);
          return (
            <Panel key={channel.id}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="font-heading text-base font-semibold text-white">
                    {channel.name}
                  </h2>
                  {channel.channel_title && (
                    <p className="mt-0.5 text-sm text-white/70">
                      Connected as: {channel.channel_title}
                    </p>
                  )}
                </div>
                <StatusPill tone={tone} label={label} />
              </div>

              {!channel.configured && (
                <p className="mt-3 text-sm text-white/50">
                  Not set up yet — missing{" "}
                  {channel.missing.map((m) => (
                    <code key={m} className="mx-0.5 text-white/70">
                      {m}
                    </code>
                  ))}
                  . There's no in-app Connect button for this — it's a one-time OAuth setup in
                  Google Cloud Console that only an admin can do; see{" "}
                  <code className="text-white/70">YOUTUBE_SETUP.md</code> in the repo for the
                  exact steps, then add the values in your deployment's environment config.
                </p>
              )}

              {channel.configured && channel.connected === false && (
                <p className="mt-3 text-sm text-amber-300">
                  {channel.error ?? "The credentials are set but the live check failed."} The
                  refresh token may need to be regenerated — see{" "}
                  <code className="text-white/70">YOUTUBE_SETUP.md</code>.
                </p>
              )}

              {channel.configured && channel.connected === true && (
                <p className="mt-3 text-sm text-white/50">
                  Capabilities: upload as private (always), and explicit publish to make a
                  specific video public — never automatic.
                </p>
              )}
            </Panel>
          );
        })}
      </div>

      <p className="mt-6 text-xs text-white/40">
        Uploads always start private. Nothing on this page, or anywhere else, can make a video
        public by itself — that's always a separate, explicit action on the video's own page.
      </p>
    </div>
  );
}
