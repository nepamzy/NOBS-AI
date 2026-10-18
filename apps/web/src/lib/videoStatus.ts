import type { SourceVideo, Video } from "../api/types";
import type { Tone } from "../components/ui";

/** The backend's PipelineStage enum has a FAILED value, but nothing in the
 * real pipeline (services/ai/orchestration/pipeline.py) ever assigns it —
 * a blocked stage just stops with `stage_detail` explaining why, and
 * `stage` itself stays wherever it got stuck. So `stage === "failed"` is
 * checked here for forward-compatibility only; the real, current signal
 * for "this needs attention" is a non-empty stage_detail on a video that
 * isn't simply waiting at the normal storyboard-approval checkpoint. */
export function isBlocked(video: Video): boolean {
  if (video.stage === "failed") return true;
  if (video.stage === "completed") return false;
  if (video.stage === "storyboard_review") return false;
  return video.stage_detail.trim() !== "";
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
