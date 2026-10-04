import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { VideoFeedback } from "../api/types";

export function ProjectFeedback({ projectId }: { projectId: string }) {
  const [feedback, setFeedback] = useState<VideoFeedback[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    // Optional section — on failure it just stays hidden, like when empty.
    api
      .listProjectFeedback(projectId)
      .then(setFeedback)
      .catch(() => setFeedback([]));
  }, [projectId]);

  if (feedback.length === 0) return null;

  return (
    <div className="mt-8">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 text-sm font-medium uppercase tracking-wide text-white/50 hover:text-white/70"
      >
        {open ? "▾" : "▸"} What it's learned ({feedback.length})
      </button>
      <p className="mt-1 text-xs text-white/40">
        Every note you've left on a finished video — the script writer reads these before writing
        the next one for this project.
      </p>
      {open && (
        <ul className="mt-3 flex flex-col gap-2">
          {feedback.map((f) => (
            <li
              key={f.id}
              className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80"
            >
              <p>{f.note}</p>
              <p className="mt-1 text-xs text-white/35">
                {new Date(f.created_at).toLocaleDateString()}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
