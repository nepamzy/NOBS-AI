import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Project } from "../api/types";

export function CreateVideo() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState<string>("");
  const [newProjectName, setNewProjectName] = useState("");
  const [topic, setTopic] = useState("");
  const [durationMinutes, setDurationMinutes] = useState(3);
  const [voicePreset, setVoicePreset] = useState("");
  const [stylePreset, setStylePreset] = useState("");
  const [runResearch, setRunResearch] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listProjects().then(setProjects).catch(() => setProjects([]));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      let targetProjectId = projectId;
      if (!targetProjectId) {
        const project = await api.createProject(newProjectName || topic.slice(0, 60));
        targetProjectId = project.id;
      }

      const video = await api.createVideo({
        project_id: targetProjectId,
        topic,
        target_duration_seconds: durationMinutes * 60,
        voice_preset: voicePreset,
        style_preset: stylePreset,
        run_research: runResearch,
      });

      navigate(`/videos/${video.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-semibold text-white">Create a video</h1>
      <p className="mt-1 text-white/60">
        Give NOBS AI a topic. It'll research, script, and storyboard it — nothing generates until
        you approve the storyboard.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-5">
        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-white/70">Project</span>
          <select
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-white"
          >
            <option value="">New project</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>

        {!projectId && (
          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-white/70">New project name (optional)</span>
            <input
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              placeholder="Defaults to the topic"
              className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-white placeholder:text-white/30"
            />
          </label>
        )}

        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-white/70">Topic</span>
          <textarea
            required
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. 5 mistakes new developers make"
            rows={3}
            className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-white placeholder:text-white/30"
          />
        </label>

        <div className="grid grid-cols-3 gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-white/70">Duration (min)</span>
            <input
              type="number"
              min={1}
              max={20}
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(Number(e.target.value))}
              className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-white"
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-white/70">Voice</span>
            <input
              value={voicePreset}
              onChange={(e) => setVoicePreset(e.target.value)}
              placeholder="default"
              className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-white placeholder:text-white/30"
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-white/70">Style</span>
            <input
              value={stylePreset}
              onChange={(e) => setStylePreset(e.target.value)}
              placeholder="default"
              className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-white placeholder:text-white/30"
            />
          </label>
        </div>

        <label className="flex items-center gap-2 text-sm text-white/70">
          <input
            type="checkbox"
            checked={runResearch}
            onChange={(e) => setRunResearch(e.target.checked)}
          />
          Let NOBS AI research the topic
        </label>

        {error && (
          <p className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting || !topic}
          className="w-fit rounded-md bg-white px-4 py-2 text-sm font-medium text-black disabled:opacity-40"
        >
          {submitting ? "Creating…" : "Create Video"}
        </button>
      </form>
    </div>
  );
}
