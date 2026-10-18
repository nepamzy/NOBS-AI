import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import type { Project, Video } from "../api/types";
import { LoadingState } from "../components/LoadingState";
import { PipelineStatus } from "../components/PipelineStatus";
import { ProjectFeedback } from "../components/ProjectFeedback";
import { Button, ErrorState, Panel } from "../components/ui";
import { UploadSchedules } from "../components/UploadSchedules";

export function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [projectError, setProjectError] = useState<string | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [videosError, setVideosError] = useState<string | null>(null);
  const [restartingId, setRestartingId] = useState<string | null>(null);
  const [restartError, setRestartError] = useState<string | null>(null);
  const [continuingId, setContinuingId] = useState<string | null>(null);

  async function continueVideo(video: Video) {
    setContinuingId(video.id);
    setRestartError(null);
    try {
      const updated = await api.continueVideo(video.id);
      setVideos((prev) => prev.map((v) => (v.id === updated.id ? updated : v)));
    } catch (err) {
      setRestartError(errorMessage(err));
    } finally {
      setContinuingId(null);
    }
  }

  async function restartVideo(video: Video) {
    const confirmed = window.confirm(
      `Restart "${video.topic}" from the beginning? Its current script, scenes, voiceover and clips will be deleted and production starts over.`,
    );
    if (!confirmed) return;
    setRestartingId(video.id);
    setRestartError(null);
    try {
      const updated = await api.restartVideo(video.id);
      setVideos((prev) => prev.map((v) => (v.id === updated.id ? updated : v)));
    } catch (err) {
      setRestartError(errorMessage(err));
    } finally {
      setRestartingId(null);
    }
  }

  useEffect(() => {
    if (!projectId) return;
    api
      .getProject(projectId)
      .then(setProject)
      .catch((err) => setProjectError(errorMessage(err)));
    api
      .listVideos(projectId)
      .then(setVideos)
      .catch((err) => setVideosError(errorMessage(err)));
  }, [projectId]);

  if (projectError)
    return <ErrorState message={`Couldn't load project: ${projectError}`} />;
  if (!project) return <LoadingState />;

  return (
    <div>
      <h1 className="font-heading text-2xl font-semibold break-words text-white">
        {project.name}
      </h1>

      <ul className="mt-6 flex flex-col gap-3">
        {videos.map((video) => (
          <li key={video.id}>
            <Link to={`/videos/${video.id}`}>
              <Panel className="hover:border-white/20">
                <p className="text-white">{video.topic}</p>
                <div className="mt-2">
                  <PipelineStatus stage={video.stage} />
                </div>
              </Panel>
            </Link>
            <div className="mt-2 flex justify-end gap-2">
              {video.stage === "failed" && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => continueVideo(video)}
                  disabled={continuingId === video.id}
                >
                  {continuingId === video.id ? "Continuing…" : "Continue"}
                </Button>
              )}
              <Button
                variant="secondary"
                size="sm"
                onClick={() => restartVideo(video)}
                disabled={restartingId === video.id}
              >
                {restartingId === video.id ? "Restarting…" : "Restart production"}
              </Button>
            </div>
          </li>
        ))}
        {restartError && <ErrorState message={`Couldn't restart: ${restartError}`} />}
        {videosError && (
          <ErrorState message={`Couldn't load videos: ${videosError}`} />
        )}
        {!videosError && videos.length === 0 && (
          <p className="text-white/50">No videos in this project yet.</p>
        )}
      </ul>

      <UploadSchedules projectId={project.id} />
      <ProjectFeedback projectId={project.id} />
    </div>
  );
}
