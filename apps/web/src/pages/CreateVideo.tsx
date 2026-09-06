import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Project } from "../api/types";

const STEPS = ["Topic", "Details", "Review"];

export function CreateVideo() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
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
    api
      .getSettings()
      .then((s) => {
        setDurationMinutes(s.default_duration_minutes);
        setVoicePreset(s.default_voice_preset);
        setStylePreset(s.default_style_preset);
      })
      .catch(() => {});
  }, []);

  async function handleCreate() {
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

  const projectLabel = projectId
    ? (projects.find((p) => p.id === projectId)?.name ?? "")
    : newProjectName || topic.slice(0, 60) || "(untitled)";

  return (
    <div className="max-w-2xl">
      <h1 className="font-heading text-2xl font-semibold text-white">Create a video</h1>
      <p className="mt-1 text-white/60">
        Give NOBS AI a topic. It'll research, script, and storyboard it — nothing generates until
        you approve the storyboard.
      </p>

      <ol className="mt-6 flex items-center gap-3">
        {STEPS.map((label, i) => (
          <li key={label} className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                  i < step
                    ? "bg-accent-500 text-black"
                    : i === step
                      ? "border-2 border-accent-500 text-accent-400"
                      : "border border-white/20 text-white/30"
                }`}
              >
                {i < step ? "✓" : i + 1}
              </span>
              <span className={`text-sm ${i === step ? "text-white" : "text-white/40"}`}>
                {label}
              </span>
            </div>
            {i < STEPS.length - 1 && <span className="h-px w-6 bg-white/10" />}
          </li>
        ))}
      </ol>

      <div className="mt-6 flex flex-col gap-5">
        {step === 0 && (
          <>
            <label className="flex flex-col gap-1.5">
              <span className="text-sm text-white/70">Topic</span>
              <textarea
                autoFocus
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g. 5 mistakes new developers make"
                rows={4}
                className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-white placeholder:text-white/30"
              />
            </label>

            <label className="flex items-center gap-2 text-sm text-white/70">
              <input
                type="checkbox"
                checked={runResearch}
                onChange={(e) => setRunResearch(e.target.checked)}
              />
              Let NOBS AI research the topic
            </label>
          </>
        )}

        {step === 1 && (
          <>
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
          </>
        )}

        {step === 2 && (
          <div className="rounded-lg border border-white/10 bg-white/5 p-5">
            <dl className="flex flex-col gap-3 text-sm">
              <Row label="Topic" value={topic} />
              <Row label="Project" value={projectLabel} />
              <Row label="Duration" value={`${durationMinutes} min`} />
              <Row label="Voice" value={voicePreset || "default"} />
              <Row label="Style" value={stylePreset || "default"} />
              <Row label="Research" value={runResearch ? "Yes, research first" : "Skip research"} />
            </dl>
          </div>
        )}

        {error && (
          <p className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {error}
          </p>
        )}

        <div className="flex items-center gap-3">
          {step > 0 && (
            <button
              onClick={() => setStep((s) => s - 1)}
              className="rounded-md border border-white/10 px-4 py-2 text-sm text-white/70 hover:text-white"
            >
              Back
            </button>
          )}
          {step < STEPS.length - 1 ? (
            <button
              onClick={() => setStep((s) => s + 1)}
              disabled={step === 0 && !topic.trim()}
              className="rounded-md bg-accent-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-600 disabled:opacity-40"
            >
              Next
            </button>
          ) : (
            <button
              onClick={handleCreate}
              disabled={submitting || !topic.trim()}
              className="rounded-md bg-white px-4 py-2 text-sm font-medium text-black disabled:opacity-40"
            >
              {submitting ? "Creating…" : "Create Video"}
            </button>
          )}
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
