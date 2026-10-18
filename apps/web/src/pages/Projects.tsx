import { Film, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage, resolveStorageUrl } from "../api/client";
import type { Project, Video } from "../api/types";
import { LoadingState } from "../components/LoadingState";
import { Button, ErrorState, Panel, StatusPill, type Tone } from "../components/ui";
import { isAwaitingApproval, isBlocked } from "../lib/videoStatus";

type SortOrder = "newest" | "oldest" | "name";
type FilterKey = "all" | "in_progress" | "awaiting_approval" | "completed" | "needs_attention";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "in_progress", label: "In Progress" },
  { key: "awaiting_approval", label: "Awaiting Approval" },
  { key: "completed", label: "Completed" },
  { key: "needs_attention", label: "Needs Attention" },
];

function latestVideoFor(videos: Video[]): Video | null {
  if (videos.length === 0) return null;
  return videos
    .slice()
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];
}

function statusFor(latest: Video | null): { tone: Tone; label: string; filter: FilterKey } {
  if (!latest) return { tone: "neutral", label: "No videos yet", filter: "all" };
  if (latest.stage === "completed") return { tone: "success", label: "Completed", filter: "completed" };
  if (isBlocked(latest)) return { tone: "error", label: "Needs Attention", filter: "needs_attention" };
  if (isAwaitingApproval(latest))
    return { tone: "warning", label: "Awaiting Approval", filter: "awaiting_approval" };
  return { tone: "info", label: "Processing", filter: "in_progress" };
}

function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const hrs = Math.floor(ms / 3600000);
  if (hrs < 1) return "just now";
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function Projects() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [thumbnails, setThumbnails] = useState<Record<string, string | null>>({});
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortOrder>("newest");
  const [filter, setFilter] = useState<FilterKey>("all");

  useEffect(() => {
    api
      .listProjects()
      .then(setProjects)
      .catch((err) => setError(errorMessage(err)));
    api.listAllVideos().then(setVideos).catch(() => setVideos([]));
  }, []);

  useEffect(() => {
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

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const project = await api.createProject(newName.trim());
      setProjects((prev) => [project, ...(prev ?? [])]);
      setNewName("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setCreating(false);
    }
  }

  const videosByProject = useMemo(() => {
    const map = new Map<string, Video[]>();
    for (const video of videos) {
      const list = map.get(video.project_id) ?? [];
      list.push(video);
      map.set(video.project_id, list);
    }
    return map;
  }, [videos]);

  const visibleProjects = useMemo(() => {
    const q = search.trim().toLowerCase();
    const list = (projects ?? [])
      .filter((p) => (q ? p.name.toLowerCase().includes(q) : true))
      .filter((p) => {
        if (filter === "all") return true;
        return statusFor(latestVideoFor(videosByProject.get(p.id) ?? [])).filter === filter;
      });
    const sorted = [...list];
    if (sort === "name") sorted.sort((a, b) => a.name.localeCompare(b.name));
    else if (sort === "oldest")
      sorted.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
    else sorted.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    return sorted;
  }, [projects, search, sort, filter, videosByProject]);

  return (
    <div>
      <h1 className="font-heading text-2xl font-semibold text-white">My Projects</h1>
      <p className="mt-1 text-white/60">Manage all your video projects and track progress.</p>

      <form onSubmit={handleCreate} className="mt-6 flex max-w-md gap-2">
        <label className="sr-only" htmlFor="new-project-name">
          New project name
        </label>
        <input
          id="new-project-name"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New project name"
          className="min-w-0 flex-1 rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/30"
        />
        <Button type="submit" disabled={creating || !newName.trim()}>
          {creating ? "Creating…" : "New project"}
        </Button>
      </form>

      {error && (
        <div className="mt-3">
          <ErrorState message={error} />
        </div>
      )}

      {projects === null && !error && (
        <div className="mt-6">
          <LoadingState />
        </div>
      )}

      {projects && projects.length > 0 && (
        <>
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
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search size={14} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-white/40" />
                <label className="sr-only" htmlFor="project-search">
                  Search projects
                </label>
                <input
                  id="project-search"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search projects…"
                  className="w-48 rounded-full border border-white/10 bg-white/5 py-1.5 pr-3 pl-8 text-sm text-white placeholder:text-white/30"
                />
              </div>
              <label className="sr-only" htmlFor="project-sort">
                Sort projects
              </label>
              <select
                id="project-sort"
                value={sort}
                onChange={(e) => setSort(e.target.value as SortOrder)}
                className="rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-white"
              >
                <option value="newest">Newest first</option>
                <option value="oldest">Oldest first</option>
                <option value="name">Name (A–Z)</option>
              </select>
            </div>
          </div>

          <ul className="mt-5 flex flex-col gap-3">
            {visibleProjects.map((project) => {
              const latest = latestVideoFor(videosByProject.get(project.id) ?? []);
              const { tone, label } = statusFor(latest);
              const thumbUrl = latest ? thumbnails[latest.id] : null;
              return (
                <li key={project.id}>
                  <Link to={`/projects/${project.id}`}>
                    <Panel className="flex items-center gap-4 hover:border-white/20">
                      <span className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-black/40">
                        {thumbUrl ? (
                          <img src={thumbUrl} alt="" className="h-full w-full object-cover" />
                        ) : (
                          <Film size={22} className="text-white/20" />
                        )}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium text-white">{project.name}</p>
                        <div className="mt-1">
                          <StatusPill tone={tone} label={label} />
                        </div>
                        <p className="mt-1 text-xs text-white/40">
                          Created {timeAgo(project.created_at)}
                          {latest ? ` · ${Math.round(latest.target_duration_seconds / 60)} min target` : ""}
                        </p>
                      </div>
                    </Panel>
                  </Link>
                </li>
              );
            })}
            {visibleProjects.length === 0 && (
              <p className="text-white/50">No projects match your filters.</p>
            )}
          </ul>
        </>
      )}

      {projects && projects.length === 0 && <p className="mt-6 text-white/50">No projects yet.</p>}
    </div>
  );
}
