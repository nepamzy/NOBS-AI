import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Project } from "../api/types";
import { StatCard } from "../components/StatCard";

export function Dashboard() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listProjects().then(setProjects).catch((e) => setError(String(e)));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-white">Welcome back, Nobert</h1>
      <p className="mt-1 text-white/60">Here's where your videos stand.</p>

      <div className="mt-6 grid grid-cols-3 gap-4">
        <StatCard label="Projects" value={projects?.length ?? "—"} />
        <StatCard label="This week" value="0 / 3" />
        <StatCard label="Processing" value={0} />
      </div>

      <h2 className="mt-8 mb-3 text-sm font-medium uppercase tracking-wide text-white/50">
        Recent projects
      </h2>
      {error && <p className="text-red-400">{error}</p>}
      {projects && projects.length === 0 && (
        <p className="text-white/50">
          No projects yet.{" "}
          <Link to="/create" className="text-white underline">
            Create your first video
          </Link>
          .
        </p>
      )}
      <ul className="flex flex-col gap-2">
        {projects?.map((project) => (
          <li key={project.id}>
            <Link
              to={`/projects/${project.id}`}
              className="block rounded-md border border-white/10 bg-white/5 px-4 py-3 hover:bg-white/10"
            >
              <span className="text-white">{project.name}</span>
              <span className="ml-2 text-xs text-white/40">
                {new Date(project.created_at).toLocaleDateString()}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
