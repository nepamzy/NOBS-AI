import { Film, Play, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage, resolveStorageUrl } from "../api/client";
import type { Project, Video } from "../api/types";
import { LoadingState } from "../components/LoadingState";
import { PipelineProgress } from "../components/PipelineStatus";
import { EmptyState, ErrorState, Panel, StatusPill } from "../components/ui";
import { isBlocked, videoStatus } from "../lib/videoStatus";

type FilterKey = "all" | "published" | "drafts" | "processing" | "needs_attention";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "published", label: "Published" },
  { key: "drafts", label: "Drafts" },
  { key: "processing", label: "Processing" },
  { key: "needs_attention", label: "Needs Attention" },
];

function filterKeyOf(video: Video): FilterKey {
  if (isBlocked(video)) return "needs_attention";
  if (video.stage === "completed") return video.youtube_published ? "published" : "drafts";
  return "processing";
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function VideoLibrary() {
  const [videos, setVideos] = useState<Video[] | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState<string | null>(null);
  // video_id -> thumbnail URL, or null once we've confirmed there isn't one.
  const [thumbnails, setThumbnails] = useState<Record<string, string | null>>({});
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<FilterKey>("all");

  useEffect(() => {
    api
      .listAllVideos()
      .then(setVideos)
      .catch((err) => setError(errorMessage(err)));
    api.listProjects().then(setProjects).catch(() => setProjects([]));
  }, []);

  // Real thumbnails only — each is the actual extracted-frame asset the
  // pipeline's THUMBNAIL stage produced, fetched from the same /assets
  // endpoint the Production Control Room already uses. Only fetched for
  // completed videos, since earlier stages have nothing to find yet.
  useEffect(() => {
    if (!videos) return;
    const completed = videos.filter((v) => v.stage === "completed" && !(v.id in thumbnails));
    if (completed.length === 0) return;
    let cancelled = false;
    Promise.all(
      completed.map(async (video) => {
        try {
          const assets = await api.listAssets(video.id);
          const thumb = assets.find((a) => a.asset_type === "thumbnail");
          return [video.id, thumb ? resolveStorageUrl(thumb.url) : null] as const;
        } catch {
          return [video.id, null] as const;
        }
      }),
    ).then((results) => {
      if (cancelled) return;
      setThumbnails((prev) => {
        const next = { ...prev };
        for (const [id, url] of results) next[id] = url;
        return next;
      });
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videos]);

  const projectById = useMemo(() => new Map(projects.map((p) => [p.id, p])), [projects]);

  const filtered = useMemo(() => {
    if (!videos) return [];
    const q = search.trim().toLowerCase();
    return videos
      .filter((v) => (filter === "all" ? true : filterKeyOf(v) === filter))
      .filter((v) => (q ? v.topic.toLowerCase().includes(q) : true))
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [videos, search, filter]);

  if (error) return <ErrorState message={`Couldn't load the video library: ${error}`} />;
  if (!videos) return <LoadingState />;

  return (
    <div>
      <h1 className="font-heading text-2xl font-semibold text-white">Video Library</h1>
      <p className="mt-1 text-white/60">Browse and manage all your generated videos.</p>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                filter === f.key
                  ? "bg-gradient-to-r from-accent-600 to-accent-400 text-white"
                  : "border border-white/10 text-white/50 hover:text-white"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="relative">
          <Search size={14} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-white/40" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search videos…"
            aria-label="Search videos by topic"
            className="w-56 rounded-full border border-white/10 bg-white/5 py-1.5 pr-3 pl-8 text-sm text-white placeholder:text-white/30"
          />
        </div>
      </div>

      {videos.length === 0 && (
        <div className="mt-6">
          <EmptyState
            title="No videos yet."
            description="Finished and in-progress videos will show up here once you create one."
            actionLabel="Create a video"
            actionTo="/create"
          />
        </div>
      )}

      {videos.length > 0 && filtered.length === 0 && (
        <p className="mt-6 text-white/50">No videos match your search/filter.</p>
      )}

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((video) => {
          const { tone, label } = videoStatus(video);
          const project = projectById.get(video.project_id);
          const thumb = thumbnails[video.id];

          return (
            <Panel key={video.id} className="flex flex-col gap-3 p-0 overflow-hidden">
              <Link
                to={`/videos/${video.id}`}
                className="relative block aspect-video w-full bg-black/40"
                aria-label={`Open ${video.topic}`}
              >
                {thumb ? (
                  <img
                    src={thumb}
                    alt={`Thumbnail for ${video.topic}`}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full w-full flex-col items-center justify-center gap-1 text-white/20">
                    <Film size={22} />
                    <span className="text-xs">{video.stage === "completed" ? "No thumbnail" : "Not ready yet"}</span>
                  </div>
                )}
                {thumb && (
                  <span className="absolute inset-0 flex items-center justify-center bg-black/0 opacity-0 transition-opacity hover:bg-black/30 hover:opacity-100">
                    <Play size={28} className="text-white" fill="white" />
                  </span>
                )}
                <span className="absolute right-1.5 bottom-1.5 rounded bg-black/70 px-1.5 py-0.5 text-[11px] text-white">
                  {formatDuration(video.target_duration_seconds)}
                </span>
              </Link>

              <div className="flex flex-1 flex-col gap-2 px-4 pb-4">
                <div className="flex items-start justify-between gap-2">
                  <Link
                    to={`/videos/${video.id}`}
                    className="line-clamp-2 text-sm font-medium text-white hover:text-accent-300"
                  >
                    {video.topic}
                  </Link>
                  <StatusPill tone={tone} label={label} />
                </div>

                {video.stage !== "completed" && !isBlocked(video) && (
                  <PipelineProgress stage={video.stage} />
                )}

                <div className="mt-auto flex items-center justify-between text-xs text-white/40">
                  <span>
                    {project ? (
                      <Link
                        to={`/projects/${project.id}`}
                        className="hover:text-accent-300 hover:underline"
                      >
                        {project.name}
                      </Link>
                    ) : (
                      "Unknown project"
                    )}
                  </span>
                  <span>{new Date(video.created_at).toLocaleDateString()}</span>
                </div>

                {video.final_video_url && (
                  <a
                    href={resolveStorageUrl(video.final_video_url) ?? undefined}
                    target="_blank"
                    rel="noreferrer"
                    download
                    className="mt-1 text-xs font-medium text-accent-400 hover:text-accent-300"
                  >
                    Download
                  </a>
                )}
              </div>
            </Panel>
          );
        })}
      </div>
    </div>
  );
}
