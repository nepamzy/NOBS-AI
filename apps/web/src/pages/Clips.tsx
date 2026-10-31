import { Scissors, Upload } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError, errorMessage, resolveStorageUrl } from "../api/client";
import type { Clip, ClipJobStage, SourceVideo } from "../api/types";
import { LoadingState } from "../components/LoadingState";
import { Button, ErrorState, Panel, StatusPill, type Tone } from "../components/ui";

const STAGE_LABELS: Record<ClipJobStage, string> = {
  uploaded: "Queued",
  transcribing: "Transcribing",
  selecting_clips: "Picking clips",
  extracting: "Cutting clips",
  completed: "Done",
  failed: "Failed",
};

const STAGE_TONES: Record<ClipJobStage, Tone> = {
  uploaded: "info",
  transcribing: "info",
  selecting_clips: "info",
  extracting: "info",
  completed: "success",
  failed: "error",
};

const ACCEPTED_TYPES = "video/mp4,video/quicktime,video/x-matroska,video/webm";
// Supabase Storage's Free-plan global file size limit — see clips.py's
// _MAX_UPLOAD_BYTES. Checked here too so an oversized file fails instantly
// instead of uploading for nothing and getting rejected server-side.
const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const hrs = Math.floor(ms / 3600000);
  if (hrs < 1) return "just now";
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function Clips() {
  const [sourceVideos, setSourceVideos] = useState<SourceVideo[]>([]);
  const [clipsBySource, setClipsBySource] = useState<Record<string, Clip[]>>({});
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
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

  useEffect(() => {
    Promise.all(
      sourceVideos.map(async (sv) => [sv.id, await api.listClips(sv.id).catch(() => [])] as const),
    ).then((pairs) => setClipsBySource(Object.fromEntries(pairs)));
  }, [sourceVideos]);

  const recentClips = useMemo(
    () =>
      Object.values(clipsBySource)
        .flat()
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 6),
    [clipsBySource],
  );

  async function uploadFile(file: File) {
    setError(null);
    if (file.size > MAX_UPLOAD_BYTES) {
      setError(
        `${file.name} is ${(file.size / (1024 * 1024)).toFixed(0)}MB — that's over the ` +
          "50MB limit, so it won't be accepted. Trim or compress it first.",
      );
      return;
    }
    setUploading(true);
    try {
      await api.uploadSourceVideo(file);
      refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setUploading(false);
    }
  }

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file) await uploadFile(file);
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) uploadFile(file);
  }

  if (loading) return <LoadingState />;

  return (
    <div className="max-w-5xl">
      <h1 className="font-heading text-2xl font-semibold text-white">Smart Clipping</h1>
      <p className="mt-1 text-white/60">
        Give it an already-finished video — it transcribes, picks the best moments, cuts them, and
        ships them to your other YouTube channel. No review step by default; turn that off per
        upload if you'd rather check each one first.
      </p>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_260px]">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
          }}
          className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-12 text-center transition-colors ${
            dragging ? "border-accent-400 bg-accent-500/10" : "border-white/15 bg-white/5 hover:border-white/30"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_TYPES}
            onChange={handleFileSelect}
            className="hidden"
          />
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-accent-600 to-accent-400">
            <Upload size={20} className="text-white" />
          </span>
          <p className="font-medium text-white">
            {uploading ? "Uploading…" : "Drop a video here or click to upload"}
          </p>
          <p className="text-xs text-white/40">Supports MP4, MOV, WEBM — up to 50MB</p>
        </div>

        <Panel>
          <h3 className="text-sm font-semibold text-white">How it works</h3>
          <ol className="mt-3 flex flex-col gap-2.5 text-sm text-white/60">
            <li>1. It transcribes your video (free, local, real speech-to-text)</li>
            <li>2. The AI picks the most compelling moments</li>
            <li>3. Each one is cut on a real word boundary, never mid-sentence</li>
            <li>4. You review and download, or let it auto-ship</li>
          </ol>
        </Panel>
      </div>

      {error && (
        <div className="mt-4">
          <ErrorState message={error} />
        </div>
      )}
      {loadError && (
        <div className="mt-4">
          <ErrorState message={`Couldn't load your uploads: ${loadError}`} />
        </div>
      )}

      {recentClips.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-white/50">Recent Clips</h2>
          <div className="flex flex-col gap-2">
            {recentClips.map((clip) => (
              <RecentClipRow key={clip.id} clip={clip} />
            ))}
          </div>
        </div>
      )}

      <div className="mt-8">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-white/50">Uploads</h2>
        <div className="flex flex-col gap-6">
          {sourceVideos.length === 0 ? (
            <p className="text-sm text-white/40">No videos uploaded yet.</p>
          ) : (
            sourceVideos.map((sourceVideo) => (
              <SourceVideoCard
                key={sourceVideo.id}
                sourceVideo={sourceVideo}
                clips={clipsBySource[sourceVideo.id] ?? []}
                onChange={refresh}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function RecentClipRow({ clip }: { clip: Clip }) {
  return (
    <Panel className="flex items-center gap-3 px-4 py-2.5">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-black/40 text-white/30">
        <Scissors size={16} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm text-white">{clip.title}</p>
        <p className="text-xs text-white/40">
          Created {timeAgo(clip.created_at)} · {formatTime(clip.start_seconds)}–{formatTime(clip.end_seconds)}
        </p>
      </div>
      {clip.clip_url ? (
        <a
          href={resolveStorageUrl(clip.clip_url) ?? undefined}
          target="_blank"
          rel="noreferrer"
          download
          className="shrink-0 rounded-md border border-accent-500/30 bg-accent-500/10 px-3 py-1.5 text-xs font-medium text-accent-300 hover:bg-accent-500/20"
        >
          Download
        </a>
      ) : (
        <span className="shrink-0 text-xs text-white/40">Rendering…</span>
      )}
    </Panel>
  );
}

function SourceVideoCard({
  sourceVideo,
  clips,
  onChange,
}: {
  sourceVideo: SourceVideo;
  clips: Clip[];
  onChange: () => void;
}) {
  const [togglingAuto, setTogglingAuto] = useState(false);

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
    <Panel>
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-white">{sourceVideo.original_filename}</p>
          <div className="mt-1 flex items-center gap-2">
            <StatusPill tone={STAGE_TONES[sourceVideo.stage]} label={STAGE_LABELS[sourceVideo.stage]} />
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
    </Panel>
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
            <StatusPill tone="success" label="Published" />
          ) : clip.clip_path ? (
            <Button variant="success" size="sm" onClick={handlePublish} disabled={publishing}>
              {publishing ? "Publishing…" : "Publish"}
            </Button>
          ) : (
            <span className="text-xs text-white/40">Rendering…</span>
          )}
        </div>
      </div>
      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
    </li>
  );
}
