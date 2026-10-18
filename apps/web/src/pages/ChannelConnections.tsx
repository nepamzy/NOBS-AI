import { ExternalLink, Play } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import type { ChannelConnectionStatus } from "../api/types";
import { LoadingState } from "../components/LoadingState";
import { Button, ErrorState, Panel, StatusPill, type Tone } from "../components/ui";

function channelTone(channel: ChannelConnectionStatus): { tone: Tone; label: string } {
  if (!channel.configured) return { tone: "neutral", label: "Not connected" };
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
    <div className="max-w-4xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl font-semibold text-white">Channel Connections</h1>
          <p className="mt-1 text-white/60">Connect and manage your YouTube channels.</p>
        </div>
        <Button variant="secondary" onClick={handleRecheck} disabled={checking}>
          {checking ? "Checking…" : "Re-check"}
        </Button>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_300px]">
        <div>
          <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-white/50">
            YouTube Channels
          </h2>
          <div className="flex flex-col gap-3">
            {status.youtube_channels.map((channel) => {
              const { tone, label } = channelTone(channel);
              return (
                <Panel key={channel.id}>
                  <div className="flex items-start gap-3">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-red-600">
                      <Play size={18} className="text-white" fill="white" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <h3 className="font-heading text-base font-semibold text-white">{channel.name}</h3>
                      <div className="mt-0.5">
                        <StatusPill tone={tone} label={label} />
                      </div>
                      {channel.channel_title && (
                        <p className="mt-1 text-sm text-white/70">{channel.channel_title}</p>
                      )}
                    </div>
                  </div>

                  {!channel.configured && (
                    <p className="mt-3 text-sm text-white/50">
                      Missing{" "}
                      {channel.missing.map((m) => (
                        <code key={m} className="mx-0.5 text-white/70">
                          {m}
                        </code>
                      ))}
                      .
                    </p>
                  )}
                  {channel.configured && channel.connected === false && (
                    <p className="mt-3 text-sm text-amber-300">
                      {channel.error ?? "The credentials are set but the live check failed."}
                    </p>
                  )}
                  {channel.configured && channel.connected === true && (
                    <p className="mt-3 text-sm text-white/50">
                      Uploads as private, always. Publishing to make a video public is a separate,
                      explicit action on that video's own page — never automatic.
                    </p>
                  )}
                </Panel>
              );
            })}
          </div>
        </div>

        <Panel>
          <h3 className="text-sm font-semibold text-white">Connecting a channel</h3>
          <p className="mt-1 text-xs text-white/40">
            There's no in-app Connect button — YouTube requires a one-time OAuth setup in Google
            Cloud Console that only an admin can do.
          </p>
          <ol className="mt-3 flex flex-col gap-3 text-sm text-white/70">
            <li className="flex gap-2.5">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-white/20 text-xs">1</span>
              Create an OAuth client for the YouTube Data API in Google Cloud Console
            </li>
            <li className="flex gap-2.5">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-white/20 text-xs">2</span>
              Generate a refresh token for the channel you want to connect
            </li>
            <li className="flex gap-2.5">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-white/20 text-xs">3</span>
              Add the client ID/secret/refresh token to your deployment's environment config
            </li>
          </ol>
          <p className="mt-4 flex items-start gap-1.5 text-xs text-white/40">
            <ExternalLink size={12} className="mt-0.5 shrink-0" />
            See <code className="text-white/60">YOUTUBE_SETUP.md</code> in the repo for the exact
            steps.
          </p>
        </Panel>
      </div>
    </div>
  );
}
