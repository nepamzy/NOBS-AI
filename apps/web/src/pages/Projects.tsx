import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Project } from "../api/types";

export function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    api.listProjects().then(setProjects);
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-white">Projects</h1>
      <ul className="mt-6 flex flex-col gap-2">
        {projects.map((project) => (
          <li key={project.id}>
            <Link
              to={`/projects/${project.id}`}
              className="block rounded-md border border-white/10 bg-white/5 px-4 py-3 hover:bg-white/10"
            >
              <span className="text-white">{project.name}</span>
            </Link>
          </li>
        ))}
        {projects.length === 0 && <p className="text-white/50">No projects yet.</p>}
      </ul>
    </div>
  );
}
