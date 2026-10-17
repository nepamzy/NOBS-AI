import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage, resolveStorageUrl } from "../api/client";
import type { Project, Video } from "../api/types";
import { LoadingState } from "../components/LoadingState";
import { PipelineProgress } from "../components/PipelineStatus";
import { EmptyState, ErrorState, Panel, StatusPill, type Tone } from "../components/ui";

type StatusFilter = "all" | "completed" | "processing" | "failed";

function videoTone(video: Video): { tone: Tone; label: string } {
  if (video.stage === "completed") return { tone: "success", label: "Completed" };
  if (video.stage === "failed") return { tone: "error", label: "Failed" };
  return { tone: "info", label: "Processing" };
}

function statusFilterOf(video: Video): StatusFilter {
  if (video.stage === "completed") return "completed";
  if (video.stage === "failed") return "failed";
  return "processing";
}

export function VideoLibrary() {
  const [videos, setVideos] = useState<Video[] | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState<string | null>(null);
  // video_id -> thumbnail URL, or null once we've confirmed there isn't one.
  const [thumbnails, setThumbnails] = useState<Record<string, string | null>>({});
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

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
      .filter((v) => (statusFilter === "all" ? true : statusFilterOf(v) === statusFilter))
      .filter((v) => (q ? v.topic.toLowerCase().includes(q) : true))
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [videos, search, statusFilter]);

  if (error) return <ErrorState message={`Couldn't load the video library: ${error}`} />;
  if (!videos) return <LoadingState />;

  return (
    <div>
      <h1 className="font-heading text-2xl font-semibold text-white">Video Library</h1>
      <p className="mt-1 text-white/60">
        Every video across every project — real output files only, nothing here is a guess at
        what's finished.
      </p>

      <div className="mt-6 flex flex-wrap gap-3">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by topic…"
          aria-label="Search videos by topic"
          className="min-w-0 flex-1 rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/30"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
          aria-label="Filter by status"
          className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white"
        >
          <option value="all">All statuses</option>
          <option value="completed">Completed</option>
          <option value="processing">Processing</option>
          <option value="failed">Failed</option>
        </select>
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
          const { tone, label } = videoTone(video);
          const project = projectById.get(video.project_id);
          const thumb = thumbnails[video.id];

          return (
            <Panel key={video.id} className="flex flex-col gap-3 p-0 overflow-hidden">
              <Link
                to={`/videos/${video.id}`}
                className="block aspect-video w-full bg-black/40"
                aria-label={`Open ${video.topic}`}
              >
                {thumb ? (
                  <img
                    src={thumb}
                    alt={`Thumbnail for ${video.topic}`}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center text-white/20">
                    {video.stage === "completed" ? "No thumbnail available" : "Not ready yet"}
                  </div>
                )}
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

                {video.stage !== "completed" && video.stage !== "failed" && (
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
