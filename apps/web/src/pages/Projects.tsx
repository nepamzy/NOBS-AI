import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import type { Project, Video } from "../api/types";
import { LoadingState } from "../components/LoadingState";
import { Button, ErrorState, Panel, StatusPill, type Tone } from "../components/ui";

type SortOrder = "newest" | "oldest" | "name";

function latestStatusFor(videos: Video[]): { tone: Tone; label: string } {
  if (videos.length === 0) return { tone: "neutral", label: "No videos yet" };
  const latest = videos
    .slice()
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];
  if (latest.stage === "completed") return { tone: "success", label: "Completed" };
  if (latest.stage === "failed") return { tone: "error", label: "Failed" };
  return { tone: "info", label: "Processing" };
}

export function Projects() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortOrder>("newest");

  useEffect(() => {
    api
      .listProjects()
      .then(setProjects)
      .catch((err) => setError(errorMessage(err)));
    // Used only to derive each project's real latest-video status below —
    // never to invent a status for a project nothing has reported yet.
    api.listAllVideos().then(setVideos).catch(() => setVideos([]));
  }, []);

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
    const list = (projects ?? []).filter((p) => (q ? p.name.toLowerCase().includes(q) : true));
    const sorted = [...list];
    if (sort === "name") sorted.sort((a, b) => a.name.localeCompare(b.name));
    else if (sort === "oldest")
      sorted.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
    else sorted.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    return sorted;
  }, [projects, search, sort]);

  return (
    <div>
      <h1 className="font-heading text-2xl font-semibold text-white">Projects</h1>

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
        <div className="mt-6 flex flex-wrap gap-3">
          <label className="sr-only" htmlFor="project-search">
            Search projects
          </label>
          <input
            id="project-search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search projects…"
            className="min-w-0 flex-1 rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/30"
          />
          <label className="sr-only" htmlFor="project-sort">
            Sort projects
          </label>
          <select
            id="project-sort"
            value={sort}
            onChange={(e) => setSort(e.target.value as SortOrder)}
            className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white"
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="name">Name (A–Z)</option>
          </select>
        </div>
      )}

      {projects && (
        <ul className="mt-6 flex flex-col gap-2">
          {visibleProjects.map((project) => {
            const { tone, label } = latestStatusFor(videosByProject.get(project.id) ?? []);
            return (
              <li key={project.id}>
                <Link to={`/projects/${project.id}`}>
                  <Panel className="flex items-center justify-between gap-3 hover:border-white/20">
                    <span className="truncate break-words text-white">{project.name}</span>
                    <StatusPill tone={tone} label={label} />
                  </Panel>
                </Link>
              </li>
            );
          })}
          {projects.length === 0 && <p className="text-white/50">No projects yet.</p>}
          {projects.length > 0 && visibleProjects.length === 0 && (
            <p className="text-white/50">No projects match your search.</p>
          )}
        </ul>
      )}
    </div>
  );
}
