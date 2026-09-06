import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Asset, Script, Video } from "../api/types";
import { LoadingState } from "../components/LoadingState";
import { PipelineProgress, PipelineStatus, StageBlockedNotice } from "../components/PipelineStatus";
import { StoryboardTimeline } from "../components/StoryboardTimeline";

const ASSET_LABELS: Record<Asset["asset_type"], string> = {
  script: "Script",
  voiceover: "Voiceover",
  scene_clip: "Scene clip",
  thumbnail: "Thumbnail",
  captions: "Captions",
  final_video: "Final video",
};

export function VideoDetail() {
  const { videoId } = useParams<{ videoId: string }>();
  const [video, setVideo] = useState<Video | null>(null);
  const [script, setScript] = useState<Script | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!videoId) return;
    api.getVideo(videoId).then(setVideo);
    api
      .getVideoScript(videoId)
      .then(setScript)
      .catch(() => setScript(null));
    api.listAssets(videoId).then(setAssets);
  }, [videoId]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 3000);
    return () => clearInterval(interval);
  }, [refresh]);

  async function handleApprove() {
    if (!videoId) return;
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
      prev
        ? { ...prev, scenes: prev.scenes.map((s) => (s.id === sceneId ? updated : s)) }
        : prev,
    );
  }

  async function handleSceneRegenerate(sceneId: string) {
    if (!videoId) return;
    const updated = await api.regenerateScene(videoId, sceneId);
    setScript((prev) =>
      prev
        ? { ...prev, scenes: prev.scenes.map((s) => (s.id === sceneId ? updated : s)) }
        : prev,
    );
  }

  if (!video) return <LoadingState />;

  const locked = video.storyboard_approved;
  const awaitingApproval = video.stage === "storyboard_review" && !locked;

  return (
    <div className="max-w-3xl">
      <h1 className="font-heading text-2xl font-semibold text-white">{video.topic}</h1>
      <p className="mt-1 text-sm text-white/50">
        Target: {Math.round(video.target_duration_seconds / 60)} min
      </p>

      <div className="mt-5">
        <PipelineStatus stage={video.stage} />
      </div>
      <div className="mt-3 max-w-sm">
        <PipelineProgress stage={video.stage} />
      </div>
      <StageBlockedNotice detail={video.stage_detail} />

      {script && (
        <div className="mt-8">
          <h2 className="font-heading text-lg font-medium text-white">{script.title}</h2>
          <p className="mt-1 text-sm italic text-white/60">"{script.hook}"</p>

          <div className="mt-4">
            <StoryboardTimeline
              scenes={script.scenes}
              targetDurationSeconds={video.target_duration_seconds}
            />
          </div>

          <ol className="mt-4 flex flex-col gap-3">
            {script.scenes.map((scene) => (
              <SceneCard
                key={scene.id}
                scene={scene}
                locked={locked}
                onSave={handleSceneSave}
                onRegenerate={handleSceneRegenerate}
              />
            ))}
          </ol>

          {awaitingApproval && (
            <div className="mt-6 rounded-lg border border-accent-500/30 bg-accent-500/5 p-5">
              <h3 className="font-heading text-base font-semibold text-white">
                Ready to generate?
              </h3>
              <p className="mt-1 text-sm text-white/60">
                {script.scenes.length} scenes,{" "}
                {script.scenes.reduce((sum, s) => sum + s.duration_seconds, 0)}s planned. This is
                the last stop before anything paid runs — review the scenes above before
                approving.
              </p>
              <button
                onClick={handleApprove}
                disabled={approving}
                className="mt-4 rounded-md bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-black transition-colors hover:bg-emerald-400 disabled:opacity-40"
              >
                {approving ? "Approving…" : "Approve Storyboard"}
              </button>
              <p className="mt-2 text-xs text-white/40">
                Nothing gets generated until you approve — voice/video generation is paid and
                needs a separate approval too.
              </p>
            </div>
          )}
          {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
        </div>
      )}

      <div className="mt-8">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-white/50">Assets</h2>
        {assets.length === 0 ? (
          <p className="text-sm text-white/40">
            No assets yet — they'll appear here as voice, video, and render steps run.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {assets.map((asset) => (
              <li
                key={asset.id}
                className="flex items-center justify-between rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm"
              >
                <span className="text-white">{asset.label || ASSET_LABELS[asset.asset_type]}</span>
                <span className="text-xs text-white/40">{asset.path}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function SceneCard({
  scene,
  locked,
  onSave,
  onRegenerate,
}: {
  scene: Script["scenes"][number];
  locked: boolean;
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
    <li className="flex gap-3 rounded-md border border-white/10 bg-white/5 p-4">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-500/15 text-xs font-semibold text-accent-400">
        {scene.order}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between">
          <span className="text-xs text-white/40">
            {scene.duration_seconds}s · {scene.transition}
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
              <button
                onClick={() => setEditing((v) => !v)}
                className="text-xs text-white/50 hover:text-white"
              >
                {editing ? "Cancel" : "Edit"}
              </button>
            </div>
          )}
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
            <button
              onClick={save}
              disabled={saving}
              className="w-fit rounded-md bg-white px-3 py-1 text-xs font-medium text-black disabled:opacity-40"
            >
              {saving ? "Saving…" : "Save"}
            </button>
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
    </li>
  );
}
