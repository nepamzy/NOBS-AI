import { FileText, ScrollText, Settings as SettingsIcon, SlidersHorizontal, Terminal } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError, errorMessage, resolveStorageUrl } from "../api/client";
import type { Asset, Script, Video } from "../api/types";
import { LoadingState } from "../components/LoadingState";
import { PipelineStepper, StageBlockedNotice, stageIndexOf } from "../components/PipelineStatus";
import { StoryboardTimeline } from "../components/StoryboardTimeline";
import { Button, ErrorState, Panel, StatusPill } from "../components/ui";
import { VideoPublishing } from "../components/VideoPublishing";
import { isBlocked, videoStatus } from "../lib/videoStatus";

const ASSET_LABELS: Record<Asset["asset_type"], string> = {
  script: "Script",
  voiceover: "Voiceover",
  scene_clip: "Scene clip",
  thumbnail: "Thumbnail",
  captions: "Captions",
  final_video: "Final video",
};

type Tab = "scenes" | "script" | "storyboard" | "logs" | "settings";
const TABS: { key: Tab; label: string; icon: typeof FileText }[] = [
  { key: "scenes", label: "Scenes", icon: FileText },
  { key: "script", label: "Script", icon: ScrollText },
  { key: "storyboard", label: "Storyboard", icon: SlidersHorizontal },
  { key: "logs", label: "Logs", icon: Terminal },
  { key: "settings", label: "Settings", icon: SettingsIcon },
];

/** Real, derived per-scene voice/video status — the API has no per-scene
 * progress field, so this is read off the video's own real stage relative
 * to the voice/video_generation stages, applied uniformly to every scene.
 * Coarser than "exact per-scene" but never invented. */
function sceneSubStatus(video: Video): { voice: string; videoGen: string } {
  const current = stageIndexOf(video.stage);
  const voiceIdx = stageIndexOf("voice");
  const videoIdx = stageIndexOf("video_generation");
  const of = (idx: number) => (current > idx ? "Completed" : current === idx ? "Processing" : "Pending");
  return { voice: of(voiceIdx), videoGen: of(videoIdx) };
}

export function VideoDetail() {
  const { videoId } = useParams<{ videoId: string }>();
  const [video, setVideo] = useState<Video | null>(null);
  const [script, setScript] = useState<Script | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [approving, setApproving] = useState(false);
  const [restarting, setRestarting] = useState(false);
  const [continuing, setContinuing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("scenes");

  const refresh = useCallback(() => {
    if (!videoId) return;
    api
      .getVideo(videoId)
      .then((v) => {
        setVideo(v);
        setLoadError(null);
      })
      .catch((err) => setLoadError(errorMessage(err)));
    api
      .getVideoScript(videoId)
      .then(setScript)
      .catch(() => setScript(null));
    api
      .listAssets(videoId)
      .then(setAssets)
      .catch(() => {});
  }, [videoId]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 3000);
    return () => clearInterval(interval);
  }, [refresh]);

  async function handleRestart() {
    if (!videoId || !video) return;
    const confirmed = window.confirm(
      "Restart this video from the beginning? Its current script, scenes, voiceover and clips will be deleted and production starts over.",
    );
    if (!confirmed) return;
    setRestarting(true);
    setError(null);
    try {
      const updated = await api.restartVideo(videoId);
      setVideo(updated);
      setScript(null);
      setAssets([]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setRestarting(false);
    }
  }

  async function handleContinue() {
    if (!videoId || !video) return;
    setContinuing(true);
    setError(null);
    try {
      setVideo(await api.continueVideo(videoId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setContinuing(false);
    }
  }

  async function handleApprove() {
    if (!videoId) return;
    const confirmed = window.confirm(
      "Approve this storyboard? This kicks off voice and video generation for every scene — " +
        "the first step that can actually cost money or GPU time. Review the scenes above first.",
    );
    if (!confirmed) return;
    setApproving(true);
    setError(null);
    try {
      const updated = await api.approveStoryboard(videoId);
      setVideo(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setApproving(false);
    }
  }

  async function handleSceneSave(sceneId: string, narration: string, visualPrompt: string) {
    if (!videoId) return;
    const updated = await api.updateScene(videoId, sceneId, {
      narration,
      visual_prompt: visualPrompt,
    });
    setScript((prev) =>
      prev ? { ...prev, scenes: prev.scenes.map((s) => (s.id === sceneId ? updated : s)) } : prev,
    );
  }

  async function handleSceneRegenerate(sceneId: string) {
    if (!videoId) return;
    const updated = await api.regenerateScene(videoId, sceneId);
    setScript((prev) =>
      prev ? { ...prev, scenes: prev.scenes.map((s) => (s.id === sceneId ? updated : s)) } : prev,
    );
  }

  if (!video) {
    return loadError ? <ErrorState message={`Couldn't load video: ${loadError}`} /> : <LoadingState />;
  }

  const locked = video.storyboard_approved;
  const awaitingApproval = video.stage === "storyboard_review" && !locked;
  const { tone, label } = videoStatus(video);
  const subStatus = sceneSubStatus(video);
  const currentStageLabel = video.stage === "completed" ? "Completed" : video.stage.replace(/_/g, " ");

  return (
    <div className="max-w-5xl">
      <nav className="text-xs text-white/40">
        <Link to="/" className="hover:text-white/70">
          Home
        </Link>{" "}
        / <Link to={`/projects/${video.project_id}`} className="hover:text-white/70">My Projects</Link> /{" "}
        <span className="text-white/60">{video.topic}</span>
      </nav>

      <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="font-heading text-2xl font-semibold text-white">{video.topic}</h1>
          <StatusPill tone={tone} label={label} />
        </div>
        <div className="flex gap-2">
          {!["topic", "storyboard_review", "completed"].includes(video.stage) && (
            <Button variant="secondary" size="sm" onClick={handleContinue} disabled={continuing}>
              {continuing ? "Continuing…" : "Continue"}
            </Button>
          )}
          <Button variant="secondary" size="sm" onClick={handleRestart} disabled={restarting}>
            {restarting ? "Restarting…" : "Restart production"}
          </Button>
        </div>
      </div>
      <p className="mt-1 text-sm text-white/50">
        Target: {Math.round(video.target_duration_seconds / 60)} min
        {video.auto_publish && (
          <span className="ml-2 rounded-full bg-amber-500/15 px-2 py-0.5 text-xs font-medium text-amber-300">
            Automated — no manual review
          </span>
        )}
      </p>

      <Panel className="mt-5 overflow-x-auto">
        <PipelineStepper stage={video.stage} failed={isBlocked(video)} />
      </Panel>

      <StageBlockedNotice detail={video.stage_detail} />

      {video.final_video_url && (
        <div className="mt-6">
          <video
            controls
            src={resolveStorageUrl(video.final_video_url) ?? undefined}
            className="w-full rounded-lg border border-white/10 bg-black"
          />
        </div>
      )}

      {video.stage === "completed" && (
        <VideoPublishing video={video} scriptTitle={script?.title ?? ""} onUpdate={setVideo} />
      )}

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_300px]">
        <div>
          <div className="flex flex-wrap gap-1 border-b border-white/10">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
                  tab === t.key
                    ? "border-accent-400 text-white"
                    : "border-transparent text-white/40 hover:text-white/70"
                }`}
              >
                <t.icon size={14} />
                {t.label}
              </button>
            ))}
          </div>

          <div className="mt-4">
            {tab === "scenes" && (
              <>
                {!script ? (
                  <p className="text-sm text-white/40">No script generated yet.</p>
                ) : (
                  <ol className="flex flex-col gap-3">
                    {script.scenes.map((scene) => (
                      <SceneCard
                        key={scene.id}
                        scene={scene}
                        locked={locked}
                        subStatus={subStatus}
                        onSave={handleSceneSave}
                        onRegenerate={handleSceneRegenerate}
                      />
                    ))}
                  </ol>
                )}
                {awaitingApproval && script && (
                  <div className="mt-6 rounded-lg border border-accent-500/30 bg-accent-500/5 p-5">
                    <h3 className="font-heading text-base font-semibold text-white">Ready to generate?</h3>
                    <p className="mt-1 text-sm text-white/60">
                      {script.scenes.length} scenes,{" "}
                      {script.scenes.reduce((sum, s) => sum + s.duration_seconds, 0)}s planned. This
                      is the last stop before anything paid runs — review the scenes above before
                      approving.
                    </p>
                    <Button variant="success" onClick={handleApprove} disabled={approving} className="mt-4">
                      {approving ? "Approving…" : "Approve Storyboard"}
                    </Button>
                    <p className="mt-2 text-xs text-white/40">
                      Nothing gets generated until you approve — voice/video generation is paid and
                      needs a separate approval too.
                    </p>
                  </div>
                )}
                {error && (
                  <div className="mt-2">
                    <ErrorState message={error} />
                  </div>
                )}
              </>
            )}

            {tab === "script" && (
              <Panel>
                {script ? (
                  <>
                    <h2 className="font-heading text-lg font-medium text-white">{script.title}</h2>
                    <p className="mt-1 text-sm italic text-white/60">&ldquo;{script.hook}&rdquo;</p>
                    <p className="mt-3 text-xs text-white/40">
                      {script.word_count} words · {script.scenes.length} scenes
                    </p>
                    <ol className="mt-4 flex flex-col gap-4">
                      {script.scenes.map((s) => (
                        <li key={s.id} className="text-sm text-white/80">
                          <span className="text-white/40">Scene {s.order}.</span> {s.narration}
                        </li>
                      ))}
                    </ol>
                  </>
                ) : (
                  <p className="text-sm text-white/40">No script generated yet.</p>
                )}
              </Panel>
            )}

            {tab === "storyboard" && (
              <Panel>
                {script ? (
                  <StoryboardTimeline scenes={script.scenes} targetDurationSeconds={video.target_duration_seconds} />
                ) : (
                  <p className="text-sm text-white/40">No storyboard yet.</p>
                )}
              </Panel>
            )}

            {tab === "logs" && (
              <Panel>
                <h3 className="text-sm font-semibold text-white">Current state</h3>
                {video.stage_detail ? (
                  <pre className="mt-2 whitespace-pre-wrap text-xs text-white/60">{video.stage_detail}</pre>
                ) : (
                  <p className="mt-2 text-sm text-white/40">No blocker — the pipeline is clear to proceed.</p>
                )}
                <h3 className="mt-5 text-sm font-semibold text-white">Assets produced</h3>
                {assets.length === 0 ? (
                  <p className="mt-2 text-sm text-white/40">None yet.</p>
                ) : (
                  <ul className="mt-2 flex flex-col gap-2">
                    {assets.map((asset) => (
                      <li key={asset.id} className="flex items-center justify-between text-sm">
                        <span className="text-white/70">{asset.label || ASSET_LABELS[asset.asset_type]}</span>
                        {asset.url && (
                          <a
                            href={resolveStorageUrl(asset.url) ?? undefined}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs text-accent-400 hover:underline"
                          >
                            Open
                          </a>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>
            )}

            {tab === "settings" && (
              <Panel>
                <dl className="flex flex-col gap-3 text-sm">
                  <Row label="Target duration" value={`${Math.round(video.target_duration_seconds / 60)} min`} />
                  <Row label="Voice preset" value={video.voice_preset || "default"} />
                  <Row label="Style preset" value={video.style_preset || "default"} />
                  <Row label="Auto-publish" value={video.auto_publish ? "On" : "Off"} />
                </dl>
                <p className="mt-4 text-xs text-white/40">
                  Read-only — there's no endpoint to change these after creation. Scene narration
                  and visuals can still be edited above, before storyboard approval.
                </p>
              </Panel>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-5">
          <Panel>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-white/50">Current Stage</h3>
            <p className="mt-1 font-heading text-base font-semibold text-white capitalize">
              {currentStageLabel}
            </p>
            <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-accent-600 to-accent-300 transition-all duration-500"
                style={{ width: `${video.stage_progress_percent}%` }}
              />
            </div>
            {video.stage_detail && (
              <p className="mt-2 text-xs text-white/40">{video.stage_detail.split("\n")[0]}</p>
            )}
          </Panel>

          <Panel>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-white/50">Recent Activity</h3>
            <p className="mt-2 text-xs text-white/40">
              Last updated {new Date(video.updated_at).toLocaleString()}
            </p>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-white/50">{label}</dt>
      <dd className="text-right text-white">{value}</dd>
    </div>
  );
}

function SceneCard({
  scene,
  locked,
  subStatus,
  onSave,
  onRegenerate,
}: {
  scene: Script["scenes"][number];
  locked: boolean;
  subStatus: { voice: string; videoGen: string };
  onSave: (id: string, narration: string, visualPrompt: string) => Promise<void>;
  onRegenerate: (id: string) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [narration, setNarration] = useState(scene.narration);
  const [visualPrompt, setVisualPrompt] = useState(scene.visual_prompt);
  const [saving, setSaving] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [regenerateError, setRegenerateError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    await onSave(scene.id, narration, visualPrompt);
    setSaving(false);
    setEditing(false);
  }

  async function regenerate() {
    setRegenerating(true);
    setRegenerateError(null);
    try {
      await onRegenerate(scene.id);
    } catch (err) {
      setRegenerateError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setRegenerating(false);
    }
  }

  return (
    <li>
      <Panel className="flex gap-3">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-500/15 text-xs font-semibold text-accent-400">
          {scene.order}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium text-white">
              Scene {scene.order} — {scene.duration_seconds}s
            </span>
            {!locked && (
              <div className="flex gap-3">
                <button
                  onClick={regenerate}
                  disabled={regenerating}
                  className="text-xs text-white/50 hover:text-white disabled:opacity-40"
                >
                  {regenerating ? "Regenerating…" : "Regenerate"}
                </button>
                <button onClick={() => setEditing((v) => !v)} className="text-xs text-white/50 hover:text-white">
                  {editing ? "Cancel" : "Edit"}
                </button>
              </div>
            )}
          </div>

          <div className="mt-1.5 flex flex-wrap gap-2">
            <StatusPill
              tone={subStatus.voice === "Completed" ? "success" : subStatus.voice === "Processing" ? "info" : "neutral"}
              label={`Voice: ${subStatus.voice}`}
            />
            <StatusPill
              tone={subStatus.videoGen === "Completed" ? "success" : subStatus.videoGen === "Processing" ? "info" : "neutral"}
              label={`Video: ${subStatus.videoGen}`}
            />
          </div>

          {editing ? (
            <div className="mt-2 flex flex-col gap-2">
              <textarea
                value={narration}
                onChange={(e) => setNarration(e.target.value)}
                rows={2}
                className="rounded-md border border-white/10 bg-black/20 px-2 py-1 text-sm text-white"
              />
              <input
                value={visualPrompt}
                onChange={(e) => setVisualPrompt(e.target.value)}
                className="rounded-md border border-white/10 bg-black/20 px-2 py-1 text-sm text-white"
              />
              <Button size="sm" onClick={save} disabled={saving} className="w-fit">
                {saving ? "Saving…" : "Save"}
              </Button>
            </div>
          ) : (
            <>
              <p className="mt-2 text-sm text-white">{scene.narration}</p>
              <p className="mt-1 text-xs text-white/40">{scene.visual_prompt}</p>
            </>
          )}

          {regenerateError && (
            <pre className="mt-3 whitespace-pre-wrap rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-200">
              {regenerateError}
            </pre>
          )}
        </div>
      </Panel>
    </li>
  );
}
