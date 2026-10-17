import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Project, Video } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { StatCard } from "../components/StatCard";
import { Button, Panel, StatusPill, type Tone } from "../components/ui";

function startOfWeek(now: Date): Date {
  const start = new Date(now);
  const day = start.getDay(); // 0 = Sunday
  const diffToMonday = day === 0 ? 6 : day - 1;
  start.setDate(start.getDate() - diffToMonday);
  start.setHours(0, 0, 0, 0);
  return start;
}

function videoTone(video: Video): { tone: Tone; label: string } {
  if (video.stage === "completed") return { tone: "success", label: "Completed" };
  if (video.stage === "failed") return { tone: "error", label: "Failed" };
  return { tone: "info", label: "Processing" };
}

export function Dashboard() {
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [videos, setVideos] = useState<Video[] | null>(null);
  const [weeklyGoal, setWeeklyGoal] = useState(3);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listProjects().then(setProjects).catch((e) => setError(String(e)));
    api.listAllVideos().then(setVideos).catch(() => setVideos([]));
    api
      .getSettings()
      .then((s) => setWeeklyGoal(s.weekly_goal))
      .catch(() => {});
  }, []);

  const weekStart = startOfWeek(new Date());
  const thisWeekCount =
    videos?.filter((v) => new Date(v.created_at) >= weekStart).length ?? 0;
  const processingCount =
    videos?.filter((v) => v.stage !== "completed" && v.stage !== "failed").length ?? 0;
  const completedCount = videos?.filter((v) => v.stage === "completed").length ?? 0;
  const latestVideos = videos
    ?.slice()
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl font-semibold text-white">
            Welcome back{user ? `, ${user.display_name}` : ""}
          </h1>
          <p className="mt-1 text-white/60">Here's where your videos stand.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/create">
            <Button variant="primary">Create a video</Button>
          </Link>
          <Link to="/projects">
            <Button variant="secondary">All projects</Button>
          </Link>
          <Link to="/library">
            <Button variant="secondary">Video library</Button>
          </Link>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Projects" value={projects?.length ?? "—"} />
        <StatCard label="Completed" value={videos ? completedCount : "—"} />
        <StatCard label="Processing" value={videos ? processingCount : "—"} />
        <StatCard label="This week" value={`${thisWeekCount} / ${weeklyGoal}`} />
      </div>

      {error && <p className="mt-4 text-red-400">{error}</p>}

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-2">
        <div>
          <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-white/50">
            Recent projects
          </h2>
          {projects && projects.length === 0 && (
            <p className="text-white/50">
              No projects yet.{" "}
              <Link to="/create" className="font-medium text-accent-400 hover:text-accent-300">
                Create your first video
              </Link>
              .
            </p>
          )}
          <ul className="flex flex-col gap-2">
            {projects?.slice(0, 5).map((project) => (
              <li key={project.id}>
                <Link to={`/projects/${project.id}`}>
                  <Panel className="flex items-center justify-between hover:border-white/20">
                    <span className="truncate text-white">{project.name}</span>
                    <span className="ml-2 shrink-0 text-xs text-white/40">
                      {new Date(project.created_at).toLocaleDateString()}
                    </span>
                  </Panel>
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-white/50">
            Latest videos
          </h2>
          {videos && videos.length === 0 && (
            <p className="text-white/50">No videos yet — they'll show up here once you create one.</p>
          )}
          <ul className="flex flex-col gap-2">
            {latestVideos?.map((video) => {
              const { tone, label } = videoTone(video);
              return (
                <li key={video.id}>
                  <Link to={`/videos/${video.id}`}>
                    <Panel className="flex items-center justify-between gap-3 hover:border-white/20">
                      <span className="truncate text-white">{video.topic}</span>
                      <StatusPill tone={tone} label={label} />
                    </Panel>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </div>
  );
}
