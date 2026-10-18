import { useEffect, useMemo, useState } from "react";
import { api, errorMessage } from "../api/client";
import type { SourceVideo, Video } from "../api/types";
import { LoadingState } from "../components/LoadingState";
import { ErrorState, Panel, StatusPill } from "../components/ui";

type DateRange = "7" | "30" | "90" | "all";

const RANGE_LABELS: Record<DateRange, string> = {
  "7": "Last 7 days",
  "30": "Last 30 days",
  "90": "Last 90 days",
  all: "All time",
};

function withinRange(dateStr: string, range: DateRange): boolean {
  if (range === "all") return true;
  const days = Number(range);
  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
  return new Date(dateStr).getTime() >= cutoff;
}

function pct(numerator: number, denominator: number): string {
  if (denominator === 0) return "—";
  return `${Math.round((numerator / denominator) * 100)}%`;
}

export function Analytics() {
  const [videos, setVideos] = useState<Video[] | null>(null);
  const [sourceVideos, setSourceVideos] = useState<SourceVideo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [range, setRange] = useState<DateRange>("30");
  const [fetchedAt] = useState(() => new Date());

  useEffect(() => {
    api
      .listAllVideos()
      .then(setVideos)
      .catch((err) => setError(errorMessage(err)));
    api
      .listSourceVideos()
      .then(setSourceVideos)
      .catch(() => setSourceVideos([]));
  }, []);

  const filtered = useMemo(
    () => videos?.filter((v) => withinRange(v.created_at, range)) ?? [],
    [videos, range],
  );

  const completed = filtered.filter((v) => v.stage === "completed").length;
  const failed = filtered.filter((v) => v.stage === "failed").length;
  const inProgress = filtered.length - completed - failed;
  const uploaded = filtered.filter((v) => v.youtube_video_id).length;
  const published = filtered.filter((v) => v.youtube_published).length;

  const filteredClips = useMemo(
    () => sourceVideos?.filter((v) => withinRange(v.created_at, range)) ?? [],
    [sourceVideos, range],
  );
  const clipsCompleted = filteredClips.filter((v) => v.stage === "completed").length;
  const clipsFailed = filteredClips.filter((v) => v.stage === "failed").length;

  if (error) return <ErrorState message={`Couldn't load analytics: ${error}`} />;
  if (!videos) return <LoadingState />;

  return (
    <div>
      <h1 className="font-heading text-2xl font-semibold text-white">Analytics</h1>
      <p className="mt-1 text-white/60">
        Production metrics are real, computed from your own projects and videos. YouTube
        performance metrics are a separate, honest story below.
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <label className="sr-only" htmlFor="analytics-range">
          Date range
        </label>
        <select
          id="analytics-range"
          value={range}
          onChange={(e) => setRange(e.target.value as DateRange)}
          className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white"
        >
          {Object.entries(RANGE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <span className="text-xs text-white/40">
          Data as of {fetchedAt.toLocaleTimeString()} — computed live from your account, not
          cached or estimated.
        </span>
      </div>

      <h2 className="mt-8 mb-3 text-sm font-medium uppercase tracking-wide text-white/50">
        Video production ({RANGE_LABELS[range].toLowerCase()})
      </h2>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Metric label="Created" value={filtered.length} />
        <Metric label="Completed" value={completed} />
        <Metric label="Failed" value={failed} />
        <Metric label="In progress" value={inProgress} />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Metric label="Completion rate" value={pct(completed, filtered.length)} />
        <Metric label="Failure rate" value={pct(failed, filtered.length)} />
      </div>

      <h2 className="mt-8 mb-3 text-sm font-medium uppercase tracking-wide text-white/50">
        Smart Clipping production
      </h2>
      {sourceVideos === null ? (
        <LoadingState />
      ) : filteredClips.length === 0 ? (
        <p className="text-sm text-white/40">No source videos uploaded in this range.</p>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Metric label="Uploaded" value={filteredClips.length} />
          <Metric label="Completed" value={clipsCompleted} />
          <Metric label="Failed" value={clipsFailed} />
        </div>
      )}

      <h2 className="mt-8 mb-3 text-sm font-medium uppercase tracking-wide text-white/50">
        YouTube
      </h2>
      <Panel>
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-white">
            Publishing activity — real, from your own videos' upload/publish state.
          </p>
          <StatusPill tone="info" label="Internal record only" />
        </div>
        <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Metric label="Uploaded to YouTube" value={uploaded} />
          <Metric label="Published (public)" value={published} />
        </div>

        <div className="mt-5 border-t border-white/10 pt-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-white">Views, watch time, and engagement</p>
            <StatusPill tone="neutral" label="Not connected" />
          </div>
          <p className="mt-1 text-xs text-white/40">
            This would need the YouTube Analytics API, which isn't integrated in this app yet —
            uploads and publishing use the YouTube Data API only. Nothing is shown here rather
            than guessed. See the Channel Connections page for what's actually wired up.
          </p>
        </div>
      </Panel>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-panel-border bg-panel p-4">
      <div className="text-xs uppercase tracking-wide text-white/50">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-white">{value}</div>
    </div>
  );
}
