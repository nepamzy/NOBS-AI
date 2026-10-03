import { useState } from "react";
import { api, ApiError } from "../api/client";
import type { Video } from "../api/types";

export function VideoPublishing({
  video,
  scriptTitle,
  onUpdate,
}: {
  video: Video;
  scriptTitle: string;
  onUpdate: (video: Video) => void;
}) {
  const [title, setTitle] = useState(scriptTitle || video.topic);
  const [description, setDescription] = useState("");
  const [uploading, setUploading] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [note, setNote] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [noteSaved, setNoteSaved] = useState(false);

  async function handleUpload() {
    setUploading(true);
    setError(null);
    try {
      const updated = await api.uploadToYoutube(video.id, { title, description });
      onUpdate(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setUploading(false);
    }
  }

  async function handlePublish() {
    const confirmed = window.confirm(
      "Make this video public on YouTube now? This can't be easily undone.",
    );
    if (!confirmed) return;
    setPublishing(true);
    setError(null);
    try {
      const updated = await api.publishToYoutube(video.id);
      onUpdate(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setPublishing(false);
    }
  }

  async function handleSaveNote(e: React.FormEvent) {
    e.preventDefault();
    if (!note.trim()) return;
    setSavingNote(true);
    try {
      await api.addVideoFeedback(video.id, note.trim());
      setNote("");
      setNoteSaved(true);
      setTimeout(() => setNoteSaved(false), 3000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setSavingNote(false);
    }
  }

  return (
    <div className="mt-8 flex flex-col gap-6">
      <div className="rounded-lg border border-white/10 bg-white/5 p-5">
        <h3 className="font-heading text-base font-semibold text-white">YouTube</h3>

        {!video.youtube_video_id ? (
          <>
            <p className="mt-1 text-sm text-white/60">
              Uploads as private — only you can see it until you explicitly publish it below.
            </p>
            <div className="mt-3 flex flex-col gap-2">
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Title"
                className="rounded-md border border-white/10 bg-black/20 px-3 py-1.5 text-sm text-white"
              />
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Description"
                rows={2}
                className="rounded-md border border-white/10 bg-black/20 px-3 py-1.5 text-sm text-white"
              />
            </div>
            <button
              onClick={handleUpload}
              disabled={uploading || !title.trim()}
              className="mt-3 rounded-md bg-accent-500 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {uploading ? "Uploading…" : "Upload to YouTube (private)"}
            </button>
          </>
        ) : video.youtube_published ? (
          <p className="mt-2 text-sm text-emerald-400">Published — live on YouTube.</p>
        ) : (
          <>
            <p className="mt-1 text-sm text-white/60">
              Uploaded as private. Watch it in YouTube Studio, then publish when you're happy
              with it — nothing makes it public until you click this.
            </p>
            <button
              onClick={handlePublish}
              disabled={publishing}
              className="mt-3 rounded-md bg-emerald-500 px-4 py-2 text-sm font-semibold text-black disabled:opacity-50"
            >
              {publishing ? "Publishing…" : "Publish (make public)"}
            </button>
          </>
        )}

        {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
      </div>

      <div className="rounded-lg border border-white/10 bg-white/5 p-5">
        <h3 className="font-heading text-base font-semibold text-white">
          Any notes for next time?
        </h3>
        <p className="mt-1 text-sm text-white/60">
          What worked, what didn't — future scripts for this project are written with your notes
          in mind.
        </p>
        <form onSubmit={handleSaveNote} className="mt-3 flex gap-2">
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="e.g. the intro dragged, keep hooks under 10 seconds"
            className="flex-1 rounded-md border border-white/10 bg-black/20 px-3 py-1.5 text-sm text-white placeholder:text-white/40"
          />
          <button
            type="submit"
            disabled={savingNote || !note.trim()}
            className="rounded-md bg-white px-4 py-1.5 text-sm font-medium text-black disabled:opacity-50"
          >
            {savingNote ? "Saving…" : "Save"}
          </button>
        </form>
        {noteSaved && <p className="mt-2 text-xs text-emerald-400">Saved.</p>}
      </div>
    </div>
  );
}
