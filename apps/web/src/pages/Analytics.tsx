import { useEffect, useMemo, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import type { SourceVideo, Video } from "../api/types";
import { LoadingState } from "../components/LoadingState";
import { ErrorState, Panel, StatusPill } from "../components/ui";
import { isBlocked, isSourceVideoBlocked } from "../lib/videoStatus";

type DateRange = "7" | "30" | "90" | "all";
type Tab = "overview" | "videos" | "audience" | "engagement";

const RANGE_LABELS: Record<DateRange, string> = {
  "7": "Last 7 days",
  "30": "Last 30 days",
  "90": "Last 90 days",
  all: "All time",
};

const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "videos", label: "Videos" },
  { key: "audience", label: "Audience" },
  { key: "engagement", label: "Engagement" },
];

function withinRange(dateStr: string, range: DateRange): boolean {
  if (range === "all") return true;
  const days = Number(range);
  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
  return new Date(dateStr).getTime() >= cutoff;
}

/** Real counts only — "videos created per day", not YouTube views, over
 * the selected range (capped at 30 points for "all time" so the chart
 * stays readable). */
function buildSeries(videos: Video[], range: DateRange): { date: string; count: number }[] {
  const days = range === "all" ? 30 : Number(range);
  const buckets: { date: string; count: number }[] = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() - i);
    buckets.push({ date: d.toLocaleDateString(undefined, { month: "short", day: "numeric" }), count: 0 });
  }
  const cutoff = new Date();
  cutoff.setHours(0, 0, 0, 0);
  cutoff.setDate(cutoff.getDate() - (days - 1));
  for (const v of videos) {
    const created = new Date(v.created_at);
    if (created < cutoff) continue;
    const idx = days - 1 - Math.floor((Date.now() - created.getTime()) / 86400000);
    if (idx >= 0 && idx < buckets.length) buckets[idx].count += 1;
  }
  return buckets;
}

export function Analytics() {
  const [videos, setVideos] = useState<Video[] | null>(null);
  const [sourceVideos, setSourceVideos] = useState<SourceVideo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [range, setRange] = useState<DateRange>("30");
  const [tab, setTab] = useState<Tab>("overview");
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
  const failed = filtered.filter(isBlocked).length;
  const inProgress = filtered.length - completed - failed;
  const uploaded = filtered.filter((v) => v.youtube_video_id).length;
  const published = filtered.filter((v) => v.youtube_published).length;

  const filteredClips = useMemo(
    () => sourceVideos?.filter((v) => withinRange(v.created_at, range)) ?? [],
    [sourceVideos, range],
  );
  const clipsCompleted = filteredClips.filter((v) => v.stage === "completed").length;
  const clipsFailed = filteredClips.filter(isSourceVideoBlocked).length;

  const series = useMemo(() => buildSeries(filtered, range), [filtered, range]);
  const recentlyCompleted = useMemo(
    () =>
      filtered
        .filter((v) => v.stage === "completed")
        .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
        .slice(0, 5),
    [filtered],
  );

  if (error) return <ErrorState message={`Couldn't load analytics: ${error}`} />;
  if (!videos) return <LoadingState />;

  return (
    <div>
      <h1 className="font-heading text-2xl font-semibold text-white">Analytics</h1>
      <p className="mt-1 text-white/60">Track your video production and channel growth.</p>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1 rounded-lg border border-white/10 bg-white/5 p-1">
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
      </div>
      <p className="mt-2 text-xs text-white/40">
        Data as of {fetchedAt.toLocaleTimeString()} — computed live from your account, not cached
        or estimated.
      </p>

      {tab === "overview" && (
        <>
          <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Metric label="Created" value={filtered.length} />
            <Metric label="Completed" value={completed} />
            <Metric label="In progress" value={inProgress} />
            <Metric label="Needs Attention" value={failed} />
          </div>

          <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-[1fr_280px]">
            <Panel>
              <h3 className="text-sm font-semibold text-white">Videos Produced Over Time</h3>
              <p className="text-xs text-white/40">
                Real video creation counts — not YouTube views (not connected; see below).
              </p>
              <div className="mt-3 h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={series} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                    <XAxis dataKey="date" tick={{ fill: "#ffffff60", fontSize: 11 }} axisLine={{ stroke: "#ffffff1a" }} tickLine={false} />
                    <YAxis allowDecimals={false} tick={{ fill: "#ffffff60", fontSize: 11 }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{ background: "#11172b", border: "1px solid #ffffff1a", borderRadius: 8, fontSize: 12 }}
                      labelStyle={{ color: "#fff" }}
                    />
                    <Line type="monotone" dataKey="count" name="Videos created" stroke="#a78bfa" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Panel>

            <Panel>
              <h3 className="text-sm font-semibold text-white">Recently Completed</h3>
              {recentlyCompleted.length === 0 ? (
                <p className="mt-2 text-sm text-white/40">None yet in this range.</p>
              ) : (
                <ul className="mt-3 flex flex-col gap-2">
                  {recentlyCompleted.map((v) => (
                    <li key={v.id}>
                      <Link to={`/videos/${v.id}`} className="block truncate text-sm text-accent-300 hover:text-accent-200">
                        {v.topic}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
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
              <Metric label="Needs Attention" value={clipsFailed} />
            </div>
          )}

          <h2 className="mt-8 mb-3 text-sm font-medium uppercase tracking-wide text-white/50">YouTube</h2>
          <Panel>
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm text-white">Publishing activity — real, from your own videos' upload/publish state.</p>
              <StatusPill tone="info" label="Internal record only" />
            </div>
            <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Metric label="Uploaded to YouTube" value={uploaded} />
              <Metric label="Published (public)" value={published} />
            </div>
          </Panel>
        </>
      )}

      {tab === "videos" && (
        <div className="mt-6 flex flex-col gap-2">
          {filtered.length === 0 && <p className="text-sm text-white/40">No videos in this range.</p>}
          {filtered.map((v) => (
            <Panel key={v.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
              <Link to={`/videos/${v.id}`} className="truncate text-sm text-white hover:text-accent-300">
                {v.topic}
              </Link>
              <span className="shrink-0 text-xs text-white/40">
                {new Date(v.created_at).toLocaleDateString()} · {Math.round(v.target_duration_seconds / 60)} min
              </span>
            </Panel>
          ))}
        </div>
      )}

      {(tab === "audience" || tab === "engagement") && (
        <Panel className="mt-6">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-white">
              {tab === "audience" ? "Subscribers and viewer demographics" : "Likes, comments, watch time, and retention"}
            </p>
            <StatusPill tone="neutral" label="Not connected" />
          </div>
          <p className="mt-1 text-xs text-white/40">
            This would need the YouTube Analytics API, which isn't integrated in this app yet —
            uploads and publishing use the YouTube Data API only. Nothing is shown here rather
            than guessed. See the Channel Connections page for what's actually wired up.
          </p>
        </Panel>
      )}
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
