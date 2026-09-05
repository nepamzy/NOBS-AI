import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Project, Video } from "../api/types";
import { PipelineStatus } from "../components/PipelineStatus";

export function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);

  useEffect(() => {
    if (!projectId) return;
    api.getProject(projectId).then(setProject);
    api.listVideos(projectId).then(setVideos);
  }, [projectId]);

  if (!project) return null;

  return (
    <div>
      <h1 className="text-2xl font-semibold text-white">{project.name}</h1>

      <ul className="mt-6 flex flex-col gap-3">
        {videos.map((video) => (
          <li key={video.id}>
            <Link
              to={`/videos/${video.id}`}
              className="block rounded-md border border-white/10 bg-white/5 p-4 hover:bg-white/10"
            >
              <p className="text-white">{video.topic}</p>
              <div className="mt-2">
                <PipelineStatus stage={video.stage} />
              </div>
            </Link>
          </li>
        ))}
        {videos.length === 0 && <p className="text-white/50">No videos in this project yet.</p>}
      </ul>
    </div>
  );
}
