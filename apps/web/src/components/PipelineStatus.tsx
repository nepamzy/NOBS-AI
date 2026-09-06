import type { PipelineStage } from "../api/types";

const STAGE_ORDER: { key: PipelineStage; label: string }[] = [
  { key: "research", label: "Research" },
  { key: "script", label: "Script" },
  { key: "storyboard_review", label: "Storyboard" },
  { key: "compliance_check", label: "Compliance" },
  { key: "voice", label: "Voice" },
  { key: "video_generation", label: "Video" },
  { key: "assembly", label: "Assembly" },
  { key: "captions", label: "Captions" },
  { key: "thumbnail", label: "Thumbnail" },
];

function stageIndexOf(stage: PipelineStage): number {
  if (stage === "completed") return STAGE_ORDER.length;
  if (stage === "topic") return -1;
  return STAGE_ORDER.findIndex((s) => s.key === stage);
}

function stageStatus(stage: PipelineStage, current: PipelineStage): "done" | "current" | "pending" {
  const currentIndex = stageIndexOf(current);
  const stageIndex = stageIndexOf(stage);
  if (stageIndex < currentIndex) return "done";
  if (stageIndex === currentIndex) return "current";
  return "pending";
}

export function PipelineStatus({ stage }: { stage: PipelineStage }) {
  return (
    <ol className="flex flex-wrap gap-2">
      {STAGE_ORDER.map(({ key, label }) => {
        const status = stageStatus(key, stage);
        return (
          <li
            key={key}
            className={`rounded-full border px-3 py-1 text-xs font-medium ${
              status === "done"
                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                : status === "current"
                  ? "border-accent-400/50 bg-accent-500/15 text-accent-400"
                  : "border-white/10 bg-white/5 text-white/40"
            }`}
          >
            {label}
          </li>
        );
      })}
    </ol>
  );
}

/** Real, not fabricated: this is "how far through the pipeline's stages",
 * derived from `stage` alone — not a within-stage completion percentage,
 * since nothing in the pipeline currently produces one (voice/video
 * generation aren't wired in yet). See CLAUDE.md's "no invented
 * information" rule — this shows only what's actually known. */
export function PipelineProgress({ stage }: { stage: PipelineStage }) {
  const index = Math.max(0, stageIndexOf(stage));
  const total = STAGE_ORDER.length;
  const percent = stage === "completed" ? 100 : Math.round((index / total) * 100);
  const label =
    stage === "completed"
      ? "Completed"
      : `Step ${index + 1} of ${total}: ${STAGE_ORDER[index]?.label ?? stage}`;

  return (
    <div>
      <div className="flex items-center justify-between text-xs text-white/50">
        <span>{label}</span>
        <span>{percent}%</span>
      </div>
      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-accent-500 transition-all duration-500"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

export function StageBlockedNotice({ detail }: { detail: string }) {
  if (!detail) return null;
  const isCostWarning = detail.includes("PAYMENT / COST WARNING");
  return (
    <pre
      className={`mt-4 whitespace-pre-wrap rounded-md border p-4 text-xs ${
        isCostWarning
          ? "border-amber-500/40 bg-amber-500/10 text-amber-200"
          : "border-white/10 bg-white/5 text-white/70"
      }`}
    >
      {detail}
    </pre>
  );
}
