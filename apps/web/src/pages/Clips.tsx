import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, errorMessage, resolveStorageUrl } from "../api/client";
import type { Clip, ClipJobStage, SourceVideo } from "../api/types";
import { LoadingState } from "../components/LoadingState";

const STAGE_LABELS: Record<ClipJobStage, string> = {
  uploaded: "Queued",
  transcribing: "Transcribing",
  selecting_clips: "Picking clips",
  extracting: "Cutting clips",
  completed: "Done",
  failed: "Failed",
};

const ACCEPTED_TYPES = "video/mp4,video/quicktime,video/x-matroska,video/webm";

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function Clips() {
  const [sourceVideos, setSourceVideos] = useState<SourceVideo[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(() => {
    api
      .listSourceVideos()
      .then((videos) => {
        setSourceVideos(videos);
        setLoadError(null);
      })
      .catch((err) => setLoadError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 4000);
    return () => clearInterval(interval);
  }, [refresh]);

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await api.uploadSourceVideo(file);
      refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setUploading(false);
    }
  }

  if (loading) return <LoadingState />;

  return (
    <div className="max-w-3xl">
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row">
        <div>
          <h1 className="font-heading text-2xl font-semibold text-white">Clips</h1>
          <p className="mt-2 text-white/60">
            Give it an already-finished video — it transcribes, picks the best moments, cuts
            them, and ships them to your other YouTube channel. No review step by default; turn
            that off per upload if you'd rather check each one first.
          </p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_TYPES}
          onChange={handleFileSelect}
          className="hidden"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="shrink-0 rounded-md bg-accent-500 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {uploading ? "Uploading…" : "Upload a video"}
        </button>
      </div>

      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
      {loadError && (
        <p className="mt-3 text-sm text-red-400">Couldn't load your uploads: {loadError}</p>
      )}

      <div className="mt-8 flex flex-col gap-6">
        {!loadError && sourceVideos.length === 0 && (
          <p className="text-sm text-white/40">No videos uploaded yet.</p>
        )}
        {sourceVideos.map((sourceVideo) => (
          <SourceVideoCard key={sourceVideo.id} sourceVideo={sourceVideo} onChange={refresh} />
        ))}
      </div>
    </div>
  );
}

function SourceVideoCard({
  sourceVideo,
  onChange,
}: {
  sourceVideo: SourceVideo;
  onChange: () => void;
}) {
  const [clips, setClips] = useState<Clip[]>([]);
  const [togglingAuto, setTogglingAuto] = useState(false);

  useEffect(() => {
    api
      .listClips(sourceVideo.id)
      .then(setClips)
      .catch(() => setClips([]));
  }, [sourceVideo.id, sourceVideo.stage]);

  async function toggleAutoPublish() {
    if (sourceVideo.auto_publish) {
      const confirmed = window.confirm(
        "Turn OFF auto-ship? Clips will still be cut, but none will upload or publish to " +
          "your other channel until you press Publish on each one yourself.",
      );
      if (!confirmed) return;
    }
    setTogglingAuto(true);
    try {
      await api.updateSourceVideo(sourceVideo.id, { auto_publish: !sourceVideo.auto_publish });
      onChange();
    } finally {
      setTogglingAuto(false);
    }
  }

  return (
    <div className="rounded-lg border border-white/10 bg-white/5 p-5">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-white">{sourceVideo.original_filename}</p>
          <div className="mt-1 flex items-center gap-2">
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                sourceVideo.stage === "completed"
                  ? "bg-emerald-500/15 text-emerald-400"
                  : sourceVideo.stage === "failed"
                    ? "bg-red-500/15 text-red-400"
                    : "bg-accent-500/15 text-accent-400"
              }`}
            >
              {STAGE_LABELS[sourceVideo.stage]}
            </span>
          </div>
        </div>
        <button
          onClick={toggleAutoPublish}
          disabled={togglingAuto}
          title={
            sourceVideo.auto_publish
              ? "Clips upload and publish automatically, no review"
              : "Clips are cut but wait for you to publish each one"
          }
          className={`shrink-0 rounded-md border px-2.5 py-1 text-xs font-semibold transition-colors disabled:opacity-50 ${
            sourceVideo.auto_publish
              ? "border-amber-500/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20"
              : "border-accent-500/30 bg-accent-500/10 text-accent-300 hover:bg-accent-500/20"
          }`}
        >
          {sourceVideo.auto_publish ? "Auto-ship: ON" : "Auto-ship: OFF"}
        </button>
      </div>

      {sourceVideo.stage_detail && (
        <pre className="mt-3 whitespace-pre-wrap rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-200">
          {sourceVideo.stage_detail}
        </pre>
      )}

      {clips.length > 0 && (
        <ul className="mt-4 flex flex-col gap-2">
          {clips.map((clip) => (
            <ClipRow key={clip.id} clip={clip} onPublished={onChange} />
          ))}
        </ul>
      )}
    </div>
  );
}

function ClipRow({ clip, onPublished }: { clip: Clip; onPublished: () => void }) {
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handlePublish() {
    setPublishing(true);
    setError(null);
    try {
      await api.publishClip(clip.id);
      onPublished();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setPublishing(false);
    }
  }

  return (
    <li className="rounded-md border border-white/10 bg-black/20 p-3 text-sm">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-white">{clip.title}</p>
          <p className="mt-0.5 text-xs text-white/50">
            {formatTime(clip.start_seconds)}–{formatTime(clip.end_seconds)} · {clip.reason}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {clip.clip_url && (
            <a
              href={resolveStorageUrl(clip.clip_url) ?? undefined}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-accent-400 hover:underline"
            >
              Watch
            </a>
          )}
          {clip.youtube_published ? (
            <span className="rounded-full bg-emerald-500/15 px-2.5 py-1 text-xs font-medium text-emerald-400">
              Published
            </span>
          ) : clip.clip_path ? (
            <button
              onClick={handlePublish}
              disabled={publishing}
              className="rounded-md bg-emerald-500 px-3 py-1 text-xs font-semibold text-black disabled:opacity-50"
            >
              {publishing ? "Publishing…" : "Publish"}
            </button>
          ) : (
            <span className="text-xs text-white/40">Rendering…</span>
          )}
        </div>
      </div>
      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
    </li>
  );
}
