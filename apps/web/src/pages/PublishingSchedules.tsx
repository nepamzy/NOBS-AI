import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import type { Clip, Project, SourceVideo, UploadSchedule, Video } from "../api/types";
import { LoadingState } from "../components/LoadingState";
import { ErrorState, Panel, StatusPill, type Tone } from "../components/ui";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export function PublishingSchedules() {
  const [schedules, setSchedules] = useState<UploadSchedule[] | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [videos, setVideos] = useState<Video[]>([]);
  const [sourceVideos, setSourceVideos] = useState<SourceVideo[]>([]);
  const [clipsBySource, setClipsBySource] = useState<Record<string, Clip[]>>({});
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  function refreshSchedules() {
    api
      .listSchedules()
      .then(setSchedules)
      .catch((err) => setError(errorMessage(err)));
  }

  useEffect(() => {
    refreshSchedules();
    api.listProjects().then(setProjects).catch(() => setProjects([]));
    api.listAllVideos().then(setVideos).catch(() => setVideos([]));
    api.listSourceVideos().then(setSourceVideos).catch(() => setSourceVideos([]));
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.all(
      sourceVideos
        .filter((sv) => sv.stage === "completed")
        .map(async (sv) => [sv.id, await api.listClips(sv.id).catch(() => [])] as const),
    ).then((pairs) => {
      if (cancelled) return;
      setClipsBySource(Object.fromEntries(pairs));
    });
    return () => {
      cancelled = true;
    };
  }, [sourceVideos]);

  const projectById = useMemo(() => new Map(projects.map((p) => [p.id, p])), [projects]);

  async function runAction(id: string, action: () => Promise<unknown>) {
    setBusyId(id);
    setError(null);
    try {
      await action();
      refreshSchedules();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  function toggleEnabled(schedule: UploadSchedule) {
    return runAction(schedule.id, () =>
      api.updateSchedule(schedule.id, { enabled: !schedule.enabled }),
    );
  }

  function toggleAutomation(schedule: UploadSchedule) {
    if (!schedule.auto_publish) {
      const confirmed = window.confirm(
        "Turn automation ON for this schedule?\n\n" +
          "Videos it creates will skip storyboard review AND upload/publish to YouTube " +
          "automatically — no review step, no chance to catch a mistake before it's public.",
      );
      if (!confirmed) return Promise.resolve();
    }
    return runAction(schedule.id, () =>
      api.updateSchedule(schedule.id, { auto_publish: !schedule.auto_publish }),
    );
  }

  function deleteSchedule(schedule: UploadSchedule) {
    if (!window.confirm("Delete this schedule? This can't be undone.")) return Promise.resolve();
    return runAction(schedule.id, () => api.deleteSchedule(schedule.id));
  }

  const uploadedVideos = videos.filter((v) => v.youtube_video_id);
  const allClips = Object.values(clipsBySource).flat();
  const publishedClips = allClips.filter((c) => c.youtube_published);
  const unpublishedRenderedClips = allClips.filter((c) => !c.youtube_published && c.clip_path);

  if (error && !schedules) return <ErrorState message={error} />;
  if (!schedules) return <LoadingState />;

  return (
    <div className="max-w-3xl">
      <h1 className="font-heading text-2xl font-semibold text-white">Publishing &amp; Schedules</h1>
      <p className="mt-1 text-white/60">
        Every recurring schedule across your projects, and a real record of what's actually been
        uploaded or published. Publishing itself happens on each video's own page — this is the
        overview.
      </p>

      {error && (
        <div className="mt-3">
          <ErrorState message={error} />
        </div>
      )}

      <h2 className="mt-8 mb-3 text-sm font-medium uppercase tracking-wide text-white/50">
        Recurring schedules
      </h2>
      {schedules.length === 0 ? (
        <p className="text-sm text-white/40">
          No schedules yet — create one from a project's page.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {schedules.map((schedule) => {
            const project = projectById.get(schedule.project_id);
            return (
              <li key={schedule.id}>
                <Panel>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-white">
                        {DAYS[schedule.day_of_week]} at {schedule.trigger_time} UTC
                        {project && (
                          <>
                            {" · "}
                            <Link
                              to={`/projects/${project.id}`}
                              className="text-accent-400 hover:underline"
                            >
                              {project.name}
                            </Link>
                          </>
                        )}
                      </p>
                      <p className="truncate text-xs text-white/50">{schedule.topic}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <button
                        onClick={() => toggleEnabled(schedule)}
                        disabled={busyId === schedule.id}
                        className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50 ${
                          schedule.enabled
                            ? "bg-emerald-500/15 text-emerald-400"
                            : "bg-white/10 text-white/50"
                        }`}
                      >
                        {schedule.enabled ? "Enabled" : "Paused"}
                      </button>
                      <button
                        onClick={() => deleteSchedule(schedule)}
                        disabled={busyId === schedule.id}
                        className="text-xs text-white/40 hover:text-red-400 disabled:opacity-50"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <div className="mt-2 flex items-center justify-between gap-3 border-t border-white/10 pt-2">
                    <p className="text-xs text-white/40">
                      {schedule.auto_publish
                        ? "Automatic — uploads and publishes with no review"
                        : "Manual — you review and approve/publish each video"}
                    </p>
                    <button
                      onClick={() => toggleAutomation(schedule)}
                      disabled={busyId === schedule.id}
                      className={`shrink-0 rounded-md border px-2.5 py-1 text-xs font-semibold transition-colors disabled:opacity-50 ${
                        schedule.auto_publish
                          ? "border-amber-500/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20"
                          : "border-accent-500/30 bg-accent-500/10 text-accent-300 hover:bg-accent-500/20"
                      }`}
                    >
                      {schedule.auto_publish ? "Deactivate automation" : "Activate automation"}
                    </button>
                  </div>
                </Panel>
              </li>
            );
          })}
        </ul>
      )}

      <h2 className="mt-8 mb-3 text-sm font-medium uppercase tracking-wide text-white/50">
        Main channel — upload/publish records
      </h2>
      {uploadedVideos.length === 0 ? (
        <p className="text-sm text-white/40">Nothing uploaded to YouTube yet.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {uploadedVideos.map((video) => (
            <li key={video.id}>
              <RecordRow
                title={video.topic}
                to={`/videos/${video.id}`}
                tone={video.youtube_published ? "success" : "warning"}
                label={video.youtube_published ? "Public" : "Private (uploaded)"}
              />
            </li>
          ))}
        </ul>
      )}

      <h2 className="mt-8 mb-3 text-sm font-medium uppercase tracking-wide text-white/50">
        Secondary channel — Smart Clipping records
      </h2>
      {allClips.length === 0 ? (
        <p className="text-sm text-white/40">No clips rendered yet.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {publishedClips.map((clip) => (
            <li key={clip.id}>
              <RecordRow title={clip.title} to="/clips" tone="success" label="Published" />
            </li>
          ))}
          {unpublishedRenderedClips.map((clip) => (
            <li key={clip.id}>
              <RecordRow
                title={clip.title}
                to="/clips"
                tone="neutral"
                label="Rendered, not published"
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function RecordRow({
  title,
  to,
  tone,
  label,
}: {
  title: string;
  to: string;
  tone: Tone;
  label: string;
}) {
  return (
    <Link to={to}>
      <Panel className="flex items-center justify-between gap-3 hover:border-white/20">
        <span className="truncate text-white">{title}</span>
        <StatusPill tone={tone} label={label} />
      </Panel>
    </Link>
  );
}
