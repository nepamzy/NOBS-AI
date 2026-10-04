import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import type { Project } from "../api/types";
import { LoadingState } from "../components/LoadingState";

export function Projects() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    api
      .listProjects()
      .then(setProjects)
      .catch((err) => setError(errorMessage(err)));
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

  return (
    <div>
      <h1 className="font-heading text-2xl font-semibold text-white">Projects</h1>

      <form onSubmit={handleCreate} className="mt-6 flex max-w-md gap-2">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New project name"
          className="min-w-0 flex-1 rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/30"
        />
        <button
          type="submit"
          disabled={creating || !newName.trim()}
          className="shrink-0 rounded-md bg-accent-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-600 disabled:opacity-40"
        >
          {creating ? "Creating…" : "New project"}
        </button>
      </form>

      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}

      {projects === null && !error && (
        <div className="mt-6">
          <LoadingState />
        </div>
      )}
      {projects && (
        <ul className="mt-6 flex flex-col gap-2">
          {projects.map((project) => (
            <li key={project.id}>
              <Link
                to={`/projects/${project.id}`}
                className="block rounded-md border border-white/10 bg-white/5 px-4 py-3 hover:bg-white/10"
              >
                <span className="break-words text-white">{project.name}</span>
              </Link>
            </li>
          ))}
          {projects.length === 0 && <p className="text-white/50">No projects yet.</p>}
        </ul>
      )}
    </div>
  );
}
