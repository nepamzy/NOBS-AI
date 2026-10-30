import type { PipelineStage, SourceVideo, Video } from "../api/types";
import type { Tone } from "../components/ui";

/** An unexpected crash sets stage="failed" and records which stage it
 * crashed at inside stage_detail (app/jobs/tasks.py's _record_failure).
 * A blocked-but-not-crashed stage (approval gate, storyboard review)
 * instead just stops in place with stage_detail explaining why, leaving
 * `stage` itself wherever it got stuck — so "needs attention" has to mean
 * more than stage === "failed" alone. */
export function isBlocked(video: Video): boolean {
  if (video.stage === "failed") return true;
  if (video.stage === "completed") return false;
  if (video.stage === "storyboard_review") return false;
  return video.stage_detail.trim() !== "";
}

const CRASHED_AT = /Crashed at '([a-z_]+)'/;

/** The stepper (PipelineStepper) needs to know WHICH stage actually failed
 * to draw the rest of the sequence as done/pending correctly — passing the
 * literal "failed" value (not a real position in STAGE_ORDER) made every
 * stage show as "Pending" even when research/script/etc. had genuinely
 * finished, because stageIndexOf("failed") falls through to -1, same as
 * "topic". Mirrors the backend's own _CRASHED_AT parsing in
 * app/routers/videos.py's continue_video. Returns null when the message
 * doesn't match (an unparsed/older failure) — callers fall back to
 * treating the video as if it crashed at an unknown point. */
export function parseCrashedAtStage(stageDetail: string): PipelineStage | null {
  const match = CRASHED_AT.exec(stageDetail);
  return (match?.[1] as PipelineStage) ?? null;
}

/** What PipelineStatus/PipelineStepper/PipelineProgress should actually
 * treat as "the current stage" for a video — video.stage itself, unless
 * it's "failed", in which case these components need the real stage it
 * crashed at (see parseCrashedAtStage) to draw progress correctly instead
 * of folding every failure back to the very start. */
export function displayStage(video: Video): PipelineStage {
  if (video.stage !== "failed") return video.stage;
  return parseCrashedAtStage(video.stage_detail) ?? video.stage;
}

export function isAwaitingApproval(video: Video): boolean {
  return video.stage === "storyboard_review" && !video.storyboard_approved;
}

export function videoStatus(video: Video): { tone: Tone; label: string } {
  if (video.stage === "completed") return { tone: "success", label: "Completed" };
  if (isBlocked(video)) return { tone: "error", label: "Needs Attention" };
  if (isAwaitingApproval(video)) return { tone: "warning", label: "Awaiting Approval" };
  return { tone: "info", label: "Processing" };
}

/** Same real behavior as isBlocked above, for Smart Clipping's
 * services/clipping/pipeline.py — ClipJobStage.FAILED is likewise never
 * actually assigned; a stuck clip job just stops with stage_detail set. */
export function isSourceVideoBlocked(sourceVideo: SourceVideo): boolean {
  if (sourceVideo.stage === "failed") return true;
  if (sourceVideo.stage === "completed") return false;
  return sourceVideo.stage_detail.trim() !== "";
}
