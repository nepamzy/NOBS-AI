import { Briefcase, Check, Clapperboard, GraduationCap, Plus, Sparkles, Smile, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Project, TransitionType } from "../api/types";
import { DurationPicker } from "../components/DurationPicker";
import { MicButton } from "../components/MicButton";
import { StylePicker } from "../components/StylePicker";
import { ErrorState, Panel } from "../components/ui";
import { VoicePicker } from "../components/VoicePicker";

const PHASES = ["Idea", "Script", "Storyboard", "Approval", "Production", "Final"];

interface OwnScene {
  narration: string;
  visual_prompt: string;
  duration_seconds: number;
  transition: TransitionType;
}

function emptyScene(): OwnScene {
  return { narration: "", visual_prompt: "", duration_seconds: 6, transition: "cut" };
}

const _TRANSITIONS: TransitionType[] = ["cut", "fade", "dissolve"];

// Splits one pasted block of text (Title / Hook / "Scene N" headers /
// Narration / Visual / Duration / Transition labels — the same shape this
// app's own responses use) into structured fields, so pasting the whole
// script does the separating instead of filling in each scene by hand.
// Forgiving about label wording and whitespace; anything it can't confidently
// label is just left for manual editing below rather than guessed at.
function parseScriptText(text: string): { title: string; hook: string; scenes: OwnScene[] } {
  let title = "";
  let hook = "";
  const sceneBlocks: string[][] = [];
  let current: string[] | null = null;

  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) continue;

    if (/^scene\s*\d+\b/i.test(line)) {
      current = [];
      sceneBlocks.push(current);
      continue;
    }
    if (current) {
      current.push(line);
      continue;
    }
    const titleMatch = /^title\s*:\s*(.*)$/i.exec(line);
    if (titleMatch) {
      title = titleMatch[1].trim();
      continue;
    }
    const hookMatch = /^hook\s*:\s*(.*)$/i.exec(line);
    if (hookMatch) hook = hookMatch[1].trim();
  }

  const scenes = sceneBlocks.map((block) => {
    const scene = emptyScene();
    for (const line of block) {
      const narrationMatch = /^narration\s*:\s*(.*)$/i.exec(line);
      if (narrationMatch) {
        scene.narration = narrationMatch[1].trim();
        continue;
      }
      const visualMatch = /^visual(?:\s*description)?\s*:\s*(.*)$/i.exec(line);
      if (visualMatch) {
        scene.visual_prompt = visualMatch[1].trim();
        continue;
      }
      const durationMatch = /^duration\s*:\s*(\d+)/i.exec(line);
      if (durationMatch) {
        scene.duration_seconds = Number(durationMatch[1]);
        continue;
      }
      const transitionMatch = /^transition\s*:\s*(\w+)/i.exec(line);
      const transitionValue = transitionMatch?.[1].toLowerCase();
      if (transitionValue && (_TRANSITIONS as string[]).includes(transitionValue)) {
        scene.transition = transitionValue as TransitionType;
      }
    }
    return scene;
  });

  return { title, hook, scenes: scenes.length ? scenes : [emptyScene()] };
}

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
  const [durationSeconds, setDurationSeconds] = useState(180);
  const [voicePreset, setVoicePreset] = useState("");
  const [stylePreset, setStylePreset] = useState("");
  const [runResearch, setRunResearch] = useState(true);
  const [hasOwnScript, setHasOwnScript] = useState(false);
  const [rawScript, setRawScript] = useState("");
  const [scriptTitle, setScriptTitle] = useState("");
  const [scriptHook, setScriptHook] = useState("");
  const [ownScenes, setOwnScenes] = useState<OwnScene[]>([emptyScene()]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Re-parses on every change to the pasted block — no separate "split it
  // up" step. Fields below stay editable afterward in case a line didn't
  // parse the way it was meant to.
  function handleRawScriptChange(value: string) {
    setRawScript(value);
    if (!value.trim()) return;
    const parsed = parseScriptText(value);
    setScriptTitle(parsed.title);
    setScriptHook(parsed.hook);
    setOwnScenes(parsed.scenes);
  }

  function updateScene(index: number, patch: Partial<OwnScene>) {
    setOwnScenes((scenes) => scenes.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  }

  const ownScenesValid =
    ownScenes.length > 0 &&
    ownScenes.every((s) => s.narration.trim() && s.visual_prompt.trim() && s.duration_seconds >= 1);

  // With a pasted script, its own Title covers what the separate Topic box
  // is for — don't force filling in both just to name the same video.
  const effectiveTopic = topic.trim() || (hasOwnScript ? scriptTitle.trim() : "");
  const canSubmit = effectiveTopic && (!hasOwnScript || ownScenesValid);

  useEffect(() => {
    api.listProjects().then(setProjects).catch(() => setProjects([]));
    api
      .getSettings()
      .then((s) => {
        setDurationSeconds(s.default_duration_minutes * 60);
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
      const finalTopic = typeLabel ? `${typeLabel} video: ${effectiveTopic}` : effectiveTopic;

      let targetProjectId = projectId;
      if (!targetProjectId) {
        const project = await api.createProject(effectiveTopic.slice(0, 60) || "Untitled");
        targetProjectId = project.id;
      }
      const video = await api.createVideo({
        project_id: targetProjectId,
        topic: finalTopic,
        target_duration_seconds: durationSeconds,
        voice_preset: voicePreset,
        style_preset: stylePreset,
        run_research: runResearch,
        ...(hasOwnScript
          ? {
              own_scenes: ownScenes.map((s) => ({
                narration: s.narration.trim(),
                visual_prompt: s.visual_prompt.trim(),
                duration_seconds: s.duration_seconds,
                transition: s.transition,
              })),
              script_title: scriptTitle.trim(),
              script_hook: scriptHook.trim(),
            }
          : {}),
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
              <span className="text-sm text-white/70">
                Enter your topic or idea{hasOwnScript && " (optional — your script's Title covers this)"}
              </span>
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
                checked={hasOwnScript}
                onChange={(e) => setHasOwnScript(e.target.checked)}
              />
              I already have a script
            </label>

            {!hasOwnScript && (
              <label className="flex items-center gap-2 text-sm text-white/70">
                <input
                  type="checkbox"
                  checked={runResearch}
                  onChange={(e) => setRunResearch(e.target.checked)}
                />
                Let NOBS AI research the topic
              </label>
            )}

            {hasOwnScript && (
              <div className="mt-2 flex flex-col gap-4 rounded-lg border border-white/10 bg-black/20 p-4">
                <p className="text-xs text-white/40">
                  Skips Research and Script entirely — no LLM call, no spend — and goes
                  straight to Storyboard for your approval.
                </p>

                <label className="flex flex-col gap-1.5">
                  <span className="text-sm text-white/70">Paste your whole script</span>
                  <textarea
                    value={rawScript}
                    onChange={(e) => handleRawScriptChange(e.target.value)}
                    placeholder={
                      "Title: ...\nHook: ...\n\nScene 1\nNarration: ...\nVisual: ...\n" +
                      "Duration: 6s\nTransition: Cut\n\nScene 2\nNarration: ...\nVisual: ...\n" +
                      "Duration: 6s\nTransition: Fade"
                    }
                    rows={10}
                    className="rounded-md border border-white/10 bg-black/20 px-3 py-2 font-mono text-xs text-white placeholder:text-white/30"
                  />
                  <span className="text-xs text-white/40">
                    Paste it all in one go — Title / Hook / Scene N / Narration / Visual /
                    Duration / Transition split out into the fields below automatically.
                    Check they landed right before creating.
                  </span>
                </label>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <label className="flex flex-col gap-1.5">
                    <span className="text-sm text-white/70">Title (optional)</span>
                    <input
                      value={scriptTitle}
                      onChange={(e) => setScriptTitle(e.target.value)}
                      className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-white"
                    />
                  </label>
                  <label className="flex flex-col gap-1.5">
                    <span className="text-sm text-white/70">Hook (optional)</span>
                    <input
                      value={scriptHook}
                      onChange={(e) => setScriptHook(e.target.value)}
                      className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-white"
                    />
                  </label>
                </div>

                <div className="flex flex-col gap-3">
                  {ownScenes.map((scene, i) => (
                    <div key={i} className="rounded-md border border-white/10 bg-white/5 p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-white/50">Scene {i + 1}</span>
                        {ownScenes.length > 1 && (
                          <button
                            type="button"
                            onClick={() =>
                              setOwnScenes((scenes) => scenes.filter((_, idx) => idx !== i))
                            }
                            className="text-white/30 hover:text-red-400"
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </div>
                      <div className="mt-2 flex flex-col gap-2">
                        <textarea
                          value={scene.narration}
                          onChange={(e) => updateScene(i, { narration: e.target.value })}
                          placeholder="Narration"
                          rows={2}
                          className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm text-white placeholder:text-white/30"
                        />
                        <textarea
                          value={scene.visual_prompt}
                          onChange={(e) => updateScene(i, { visual_prompt: e.target.value })}
                          placeholder="Visual description (what the clip should show)"
                          rows={2}
                          className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm text-white placeholder:text-white/30"
                        />
                        <div className="flex gap-2">
                          <label className="flex items-center gap-1.5 text-xs text-white/50">
                            Duration
                            <input
                              type="number"
                              min={1}
                              max={60}
                              value={scene.duration_seconds}
                              onChange={(e) =>
                                updateScene(i, { duration_seconds: Number(e.target.value) })
                              }
                              className="w-16 rounded-md border border-white/10 bg-black/20 px-2 py-1 text-white"
                            />
                            s
                          </label>
                          <select
                            value={scene.transition}
                            onChange={(e) =>
                              updateScene(i, { transition: e.target.value as TransitionType })
                            }
                            className="rounded-md border border-white/10 bg-black/20 px-2 py-1 text-xs text-white"
                          >
                            <option value="cut">Cut</option>
                            <option value="fade">Fade</option>
                            <option value="dissolve">Dissolve</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <button
                  type="button"
                  onClick={() => setOwnScenes((scenes) => [...scenes, emptyScene()])}
                  className="flex items-center justify-center gap-1.5 rounded-md border border-dashed border-white/15 py-2 text-xs text-white/50 hover:border-white/30 hover:text-white"
                >
                  <Plus size={14} /> Add scene
                </button>
              </div>
            )}

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
                <DurationPicker seconds={durationSeconds} onChange={setDurationSeconds} />
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
                disabled={submitting || !canSubmit}
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
