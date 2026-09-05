import type { PipelineStage } from "../api/types";

const STAGE_ORDER: { key: PipelineStage; label: string }[] = [
  { key: "research", label: "Research" },
  { key: "script", label: "Script" },
  { key: "storyboard_review", label: "Storyboard" },
  { key: "voice", label: "Voice" },
  { key: "video_generation", label: "Video" },
  { key: "assembly", label: "Assembly" },
  { key: "captions", label: "Captions" },
  { key: "thumbnail", label: "Thumbnail" },
];

function stageStatus(stage: PipelineStage, current: PipelineStage): "done" | "current" | "pending" {
  const order = STAGE_ORDER.map((s) => s.key);
  const currentIndex = current === "completed" ? order.length : order.indexOf(current);
  const stageIndex = order.indexOf(stage);
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
            className={`rounded-full border px-3 py-1 text-xs ${
              status === "done"
                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                : status === "current"
                  ? "border-amber-400/50 bg-amber-400/10 text-amber-300"
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
