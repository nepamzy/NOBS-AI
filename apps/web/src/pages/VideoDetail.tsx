import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Script, Video } from "../api/types";
import { PipelineStatus, StageBlockedNotice } from "../components/PipelineStatus";

export function VideoDetail() {
  const { videoId } = useParams<{ videoId: string }>();
  const [video, setVideo] = useState<Video | null>(null);
  const [script, setScript] = useState<Script | null>(null);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!videoId) return;
    api.getVideo(videoId).then(setVideo);
    api
      .getVideoScript(videoId)
      .then(setScript)
      .catch(() => setScript(null));
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

  if (!video) return null;

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-semibold text-white">{video.topic}</h1>
      <p className="mt-1 text-sm text-white/50">
        Target: {Math.round(video.target_duration_seconds / 60)} min
      </p>

      <div className="mt-4">
        <PipelineStatus stage={video.stage} />
      </div>
      <StageBlockedNotice detail={video.stage_detail} />

      {script && (
        <div className="mt-8">
          <h2 className="text-lg font-medium text-white">{script.title}</h2>
          <p className="mt-1 text-sm italic text-white/60">"{script.hook}"</p>

          <ol className="mt-4 flex flex-col gap-3">
            {script.scenes.map((scene) => (
              <SceneCard key={scene.id} scene={scene} onSave={handleSceneSave} />
            ))}
          </ol>

          {video.stage === "storyboard_review" && !video.storyboard_approved && (
            <div className="mt-6">
              <button
                onClick={handleApprove}
                disabled={approving}
                className="rounded-md bg-emerald-500 px-4 py-2 text-sm font-medium text-black disabled:opacity-40"
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
    </div>
  );
}

function SceneCard({
  scene,
  onSave,
}: {
  scene: Script["scenes"][number];
  onSave: (id: string, narration: string, visualPrompt: string) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [narration, setNarration] = useState(scene.narration);
  const [visualPrompt, setVisualPrompt] = useState(scene.visual_prompt);
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    await onSave(scene.id, narration, visualPrompt);
    setSaving(false);
    setEditing(false);
  }

  return (
    <li className="rounded-md border border-white/10 bg-white/5 p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs text-white/40">
          Scene {scene.order} · {scene.duration_seconds}s · {scene.transition}
        </span>
        <button
          onClick={() => setEditing((v) => !v)}
          className="text-xs text-white/50 hover:text-white"
        >
          {editing ? "Cancel" : "Edit"}
        </button>
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
    </li>
  );
}
