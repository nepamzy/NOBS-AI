import { Briefcase, Check, Clapperboard, GraduationCap, Sparkles, Smile } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Project } from "../api/types";
import { DurationPicker } from "../components/DurationPicker";
import { MicButton } from "../components/MicButton";
import { StylePicker } from "../components/StylePicker";
import { ErrorState, Panel } from "../components/ui";
import { VoicePicker } from "../components/VoicePicker";

const PHASES = ["Idea", "Script", "Storyboard", "Approval", "Production", "Final"];

// Not a real backend field — VideoCreate has no "content type". Picking one
// here has a real effect anyway: it's folded into the topic actually sent
// to research/script generation below, instead of being decorative.
const CONTENT_TYPES = [
  { id: "educational", label: "Educational", description: "Teach something useful", icon: GraduationCap },
  { id: "entertainment", label: "Entertainment", description: "Keep people entertained", icon: Clapperboard },
  { id: "business", label: "Business", description: "Promote a product or service", icon: Briefcase },
  { id: "other", label: "Other", description: "Any other topic", icon: Smile },
] as const;

export function CreateVideo() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [showProjectPicker, setShowProjectPicker] = useState(false);
  const [contentType, setContentType] = useState<(typeof CONTENT_TYPES)[number]["id"] | null>(null);
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
      const typeLabel = CONTENT_TYPES.find((t) => t.id === contentType)?.label;
      const finalTopic = typeLabel ? `${typeLabel} video: ${topic.trim()}` : topic.trim();

      let targetProjectId = projectId;
      if (!targetProjectId) {
        const project = await api.createProject(topic.slice(0, 60) || "Untitled");
        targetProjectId = project.id;
      }
      const video = await api.createVideo({
        project_id: targetProjectId,
        topic: finalTopic,
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
    <div className="max-w-5xl">
      <h1 className="font-heading text-2xl font-semibold text-white">Create Video</h1>
      <p className="mt-1 text-white/60">Step-by-step video creation, guided end to end.</p>

      <Panel className="mt-6">
        <h2 className="font-heading text-lg font-semibold text-white">Create a New Video</h2>

        <ol className="mt-4 flex flex-wrap items-center gap-2">
          {PHASES.map((label, i) => (
            <li key={label} className="flex items-center gap-2">
              <span
                className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
                  i === 0
                    ? "bg-gradient-to-r from-accent-600 to-accent-400 text-white"
                    : "border border-white/15 text-white/40"
                }`}
              >
                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-black/20 text-[10px]">
                  {i + 1}
                </span>
                {label}
              </span>
              {i < PHASES.length - 1 && <span className="h-px w-4 bg-white/15" />}
            </li>
          ))}
        </ol>

        <div className="mt-6 grid grid-cols-1 gap-8 lg:grid-cols-[1fr_280px]">
          <div>
            <h3 className="text-base font-semibold text-white">1. Your Idea</h3>
            <p className="mt-1 text-sm text-white/50">What type of video do you want to create?</p>

            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {CONTENT_TYPES.map((t) => {
                const selected = contentType === t.id;
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setContentType(selected ? null : t.id)}
                    className={`flex items-start gap-3 rounded-lg border p-3 text-left transition-colors ${
                      selected
                        ? "border-accent-500 bg-accent-500/10"
                        : "border-white/10 bg-white/5 hover:border-white/20"
                    }`}
                  >
                    <t.icon size={18} className={selected ? "text-accent-300" : "text-white/50"} />
                    <span>
                      <span className="block text-sm font-medium text-white">{t.label}</span>
                      <span className="block text-xs text-white/40">{t.description}</span>
                    </span>
                  </button>
                );
              })}
            </div>

            <label className="mt-5 flex flex-col gap-1.5">
              <span className="text-sm text-white/70">Enter your topic or idea</span>
              <div className="flex items-start gap-2">
                <textarea
                  autoFocus
                  maxLength={300}
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. 5 habits that will change your life"
                  rows={3}
                  className="flex-1 rounded-md border border-white/10 bg-black/20 px-3 py-2 text-white placeholder:text-white/30"
                />
                <MicButton value={topic} onChange={setTopic} />
              </div>
              <span className="self-end text-xs text-white/30">{topic.length}/300</span>
            </label>

            <label className="flex items-center gap-2 text-sm text-white/70">
              <input
                type="checkbox"
                checked={runResearch}
                onChange={(e) => setRunResearch(e.target.checked)}
              />
              Let NOBS AI research the topic
            </label>

            {projects.length > 0 && (
              <div className="mt-2">
                {!showProjectPicker ? (
                  <button
                    type="button"
                    onClick={() => setShowProjectPicker(true)}
                    className="text-xs text-accent-400 hover:text-accent-300"
                  >
                    Add to an existing project instead of starting a new one
                  </button>
                ) : (
                  <label className="flex flex-col gap-1.5">
                    <span className="text-sm text-white/70">Project</span>
                    <select
                      value={projectId}
                      onChange={(e) => setProjectId(e.target.value)}
                      className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-white"
                    >
                      <option value="">New project</option>
                      {projects.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </div>
            )}

            <div className="mt-5 flex flex-col gap-4 border-t border-white/10 pt-5">
              <label className="flex flex-col gap-1.5">
                <span className="text-sm text-white/70">Duration</span>
                <DurationPicker minutes={durationMinutes} onChange={setDurationMinutes} />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-sm text-white/70">Voice</span>
                <VoicePicker value={voicePreset} onChange={setVoicePreset} compact />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-sm text-white/70">Style</span>
                <StylePicker value={stylePreset} onChange={setStylePreset} compact />
              </label>
            </div>

            {error && (
              <div className="mt-4">
                <ErrorState message={error} />
              </div>
            )}

            <div className="mt-5 flex items-center gap-3">
              <button
                type="button"
                onClick={() => navigate(-1)}
                className="rounded-md border border-white/10 px-4 py-2 text-sm text-white/70 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={submitting || !topic.trim()}
                className="rounded-md bg-gradient-to-r from-accent-600 to-accent-400 px-5 py-2 text-sm font-medium text-white disabled:opacity-40"
              >
                {submitting ? "Creating…" : "Next →"}
              </button>
            </div>
          </div>

          <div className="rounded-lg border border-white/10 bg-black/20 p-4">
            <h4 className="text-sm font-semibold text-white">Tips for better results</h4>
            <ul className="mt-3 flex flex-col gap-2.5 text-sm text-white/60">
              {[
                "Be specific about your topic",
                "Include your target audience",
                "Mention the tone you want",
                "You can edit the script later",
              ].map((tip) => (
                <li key={tip} className="flex items-start gap-2">
                  <Check size={14} className="mt-0.5 shrink-0 text-accent-400" />
                  {tip}
                </li>
              ))}
            </ul>
            <div className="mt-6 flex flex-col items-center gap-2 text-center">
              <span className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-accent-600 to-accent-300">
                <Sparkles size={20} className="text-white" />
              </span>
              <p className="text-xs text-white/40">From your idea… to a finished video.</p>
            </div>
          </div>
        </div>
      </Panel>
    </div>
  );
}
