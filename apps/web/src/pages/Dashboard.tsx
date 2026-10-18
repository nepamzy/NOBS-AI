import { AlertCircle, CheckCircle2, Clock, Film, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, resolveStorageUrl } from "../api/client";
import type { PipelineStage, Project, Video } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Panel, StatusPill, type Tone } from "../components/ui";
import { isAwaitingApproval, isBlocked, videoStatus } from "../lib/videoStatus";

/** Real thumbnails only, same /assets lookup Video Library uses — fetched
 * just for the handful of completed videos actually shown here. */
function useThumbnails(videos: Video[] | null) {
  const [thumbnails, setThumbnails] = useState<Record<string, string | null>>({});

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

  return thumbnails;
}

function Thumb({ url }: { url: string | null | undefined }) {
  return (
    <span className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-md bg-black/40">
      {url ? (
        <img src={url} alt="" className="h-full w-full object-cover" />
      ) : (
        <Film size={16} className="text-white/20" />
      )}
    </span>
  );
}

/** Real, derived "recent activity" — one line per video, summarizing its
 * current (real) stage, not a stored/invented event log (none exists). */
function activityLabel(video: Video): string {
  const labels: Partial<Record<PipelineStage, string>> = {
    research: "Researching",
    script: "Writing script",
    storyboard_review: video.storyboard_approved ? "Storyboard approved" : "Storyboard awaiting approval",
    compliance_check: "Compliance check",
    voice: "Voice generation",
    video_generation: "Video generation",
    assembly: "Assembling",
    captions: "Adding captions",
    thumbnail: "Generating thumbnail",
    completed: "Completed",
    failed: "Failed",
  };
  return labels[video.stage] ?? video.stage;
}

function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(ms / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function Dashboard() {
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [videos, setVideos] = useState<Video[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const thumbnails = useThumbnails(videos);

  useEffect(() => {
    api.listProjects().then(setProjects).catch((e) => setError(String(e)));
    api.listAllVideos().then(setVideos).catch(() => setVideos([]));
  }, []);

  const completed = videos?.filter((v) => v.stage === "completed").length ?? 0;
  const needsAttention = videos?.filter(isBlocked).length ?? 0;
  const awaitingApproval = videos?.filter(isAwaitingApproval).length ?? 0;
  const inProgress =
    videos?.filter((v) => v.stage !== "completed" && !isBlocked(v) && !isAwaitingApproval(v)).length ?? 0;

  const recentActivity = videos
    ?.slice()
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, 3);

  const projectById = new Map((projects ?? []).map((p) => [p.id, p]));
  const recentProjects = projects
    ?.slice()
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 4);
  const latestVideos = videos
    ?.slice()
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 4);
  // Each project's own thumbnail isn't a real field — shown as its most
  // recently created video's real thumbnail instead, the same honest
  // substitution Video Library makes.
  const latestVideoByProject = useMemo(() => {
    const map = new Map<string, Video>();
    for (const v of (videos ?? []).slice().sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())) {
      map.set(v.project_id, v);
    }
    return map;
  }, [videos]);

  return (
    <div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
        <div>
          <h1 className="font-heading text-2xl font-semibold text-white">
            Good {new Date().getHours() < 12 ? "morning" : new Date().getHours() < 18 ? "afternoon" : "evening"}
            , <span className="text-accent-400">{user?.display_name ?? ""}</span> 👋
          </h1>
          <p className="mt-1 text-white/60">
            Your AI-powered YouTube video production studio. Turn your ideas into professional
            videos — automatically.
          </p>

          <Link
            to="/create"
            className="mt-5 flex items-center gap-4 rounded-xl bg-gradient-to-r from-accent-600 via-accent-500 to-accent-300 p-5 transition-opacity hover:opacity-90"
          >
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-white/15">
              <Sparkles size={20} className="text-white" />
            </span>
            <span>
              <span className="block font-heading text-base font-semibold text-white">
                Create a New Video
              </span>
              <span className="block text-sm text-white/80">
                Start with a topic and let NOBS AI handle the rest.
              </span>
            </span>
          </Link>
        </div>

        <Panel>
          <h2 className="font-heading text-sm font-semibold text-white">Recent Activity</h2>
          <div className="mt-3 flex flex-col gap-3">
            {!recentActivity || recentActivity.length === 0 ? (
              <p className="text-sm text-white/40">Nothing yet — create your first video.</p>
            ) : (
              recentActivity.map((v) => (
                <Link key={v.id} to={`/videos/${v.id}`} className="flex items-start gap-2.5">
                  <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-500/15 text-accent-300">
                    <Clock size={14} />
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm text-white/90">{activityLabel(v)}</span>
                    <span className="block text-xs text-white/40">{timeAgo(v.updated_at)}</span>
                  </span>
                </Link>
              ))
            )}
          </div>
        </Panel>
      </div>

      <h2 className="mt-8 mb-3 text-sm font-medium uppercase tracking-wide text-white/50">
        Production Overview
      </h2>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <OverviewStat icon={Clock} tone="info" label="In Progress" value={videos ? inProgress : "—"} sub="videos" />
        <OverviewStat icon={Clock} tone="warning" label="Awaiting Approval" value={videos ? awaitingApproval : "—"} sub="storyboards" />
        <OverviewStat icon={CheckCircle2} tone="success" label="Completed" value={videos ? completed : "—"} sub="videos finished" />
        <OverviewStat icon={AlertCircle} tone="error" label="Needs Attention" value={videos ? needsAttention : "—"} sub="failed" />
      </div>

      {error && <p className="mt-4 text-red-400">{error}</p>}

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-2">
        <div>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-medium uppercase tracking-wide text-white/50">
              Recent Projects
            </h2>
            <Link to="/projects" className="text-xs text-accent-400 hover:text-accent-300">
              View all
            </Link>
          </div>
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
            {recentProjects?.map((project) => {
              const latest = latestVideoByProject.get(project.id);
              return (
                <li key={project.id}>
                  <Link to={`/projects/${project.id}`}>
                    <Panel className="flex items-center gap-3 hover:border-white/20">
                      <Thumb url={latest ? thumbnails[latest.id] : null} />
                      <span className="min-w-0 flex-1 truncate text-white">{project.name}</span>
                      <span className="ml-2 shrink-0 text-xs text-white/40">
                        {new Date(project.created_at).toLocaleDateString()}
                      </span>
                    </Panel>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>

        <div>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-medium uppercase tracking-wide text-white/50">
              Latest Videos
            </h2>
            <Link to="/library" className="text-xs text-accent-400 hover:text-accent-300">
              View all
            </Link>
          </div>
          {videos && videos.length === 0 && (
            <p className="text-white/50">No videos yet — they'll show up here once you create one.</p>
          )}
          <ul className="flex flex-col gap-2">
            {latestVideos?.map((video) => {
              const { tone, label } = videoStatus(video);
              return (
                <li key={video.id}>
                  <Link to={`/videos/${video.id}`}>
                    <Panel className="flex items-center gap-3 hover:border-white/20">
                      <Thumb url={thumbnails[video.id]} />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-white">{video.topic}</span>
                        <span className="block truncate text-xs text-white/40">
                          {projectById.get(video.project_id)?.name ?? ""}
                        </span>
                      </span>
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

function OverviewStat({
  icon: Icon,
  tone,
  label,
  value,
  sub,
}: {
  icon: typeof Clock;
  tone: Tone;
  label: string;
  value: number | string;
  sub: string;
}) {
  const toneClasses: Record<Tone, string> = {
    success: "bg-emerald-500/15 text-emerald-400",
    warning: "bg-amber-500/15 text-amber-400",
    error: "bg-red-500/15 text-red-400",
    info: "bg-sky-500/15 text-sky-400",
    neutral: "bg-white/10 text-white/50",
  };
  return (
    <Panel>
      <span className={`inline-flex h-9 w-9 items-center justify-center rounded-full ${toneClasses[tone]}`}>
        <Icon size={16} />
      </span>
      <div className="mt-3 text-xs uppercase tracking-wide text-white/50">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-white">{value}</div>
      <div className="text-xs text-white/40">{sub}</div>
    </Panel>
  );
}
