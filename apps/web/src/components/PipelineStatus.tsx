import { Check } from "lucide-react";
import type { PipelineStage } from "../api/types";

export const STAGE_ORDER: { key: PipelineStage; label: string }[] = [
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

export function stageIndexOf(stage: PipelineStage): number {
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

/** Circular-icon stage stepper — same real per-stage done/current/pending
 * state as PipelineStatus above, in the connected-dots layout used on the
 * Production Control Room screen (video.stage is the only source of
 * truth; "failed" shows the stage it actually failed on, in red). */
export function PipelineStepper({
  stage,
  failed,
}: {
  stage: PipelineStage;
  failed?: boolean;
}) {
  return (
    <ol className="flex flex-wrap items-start gap-x-1 gap-y-4">
      {STAGE_ORDER.map(({ key, label }, i) => {
        const status = stageStatus(key, stage);
        const isFailedHere = failed && status === "current";
        return (
          <li key={key} className="flex items-center">
            <div className="flex flex-col items-center gap-1.5">
              <span
                className={`flex h-9 w-9 items-center justify-center rounded-full border-2 ${
                  isFailedHere
                    ? "border-red-500 bg-red-500/15 text-red-400"
                    : status === "done"
                      ? "border-emerald-500 bg-emerald-500/15 text-emerald-400"
                      : status === "current"
                        ? "border-accent-400 bg-accent-500/20 text-accent-300 shadow-[0_0_12px_-1px_var(--color-accent-500)]"
                        : "border-white/15 text-white/30"
                }`}
              >
                {status === "done" ? <Check size={16} /> : <span className="h-2 w-2 rounded-full bg-current" />}
              </span>
              <span className="text-center text-[11px] leading-tight text-white/60">{label}</span>
              <span
                className={`text-[10px] font-medium ${
                  isFailedHere
                    ? "text-red-400"
                    : status === "done"
                      ? "text-emerald-400"
                      : status === "current"
                        ? "text-accent-300"
                        : "text-white/30"
                }`}
              >
                {isFailedHere ? "Failed" : status === "done" ? "Done" : status === "current" ? "In Progress" : "Pending"}
              </span>
            </div>
            {i < STAGE_ORDER.length - 1 && (
              // The connector fills as the stage completes: solid when this
              // stage is done, half and pulsing while it's running, empty
              // when it hasn't started. Real stage state, not a timer.
              <span className="relative mx-1 mb-6 h-px w-6 shrink-0 overflow-hidden bg-white/15 sm:w-10">
                <span
                  className={`absolute inset-y-0 left-0 transition-all duration-700 ${
                    status === "done"
                      ? "w-full bg-emerald-400"
                      : status === "current"
                        ? "w-1/2 animate-pulse bg-accent-400"
                        : "w-0"
                  }`}
                />
              </span>
            )}
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
