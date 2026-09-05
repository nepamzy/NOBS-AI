// Mirrors apps/api/app/schemas/* and app/models/enums.py — keep in sync by hand
// until the API ships an OpenAPI-generated client.

export type PipelineStage =
  | "topic"
  | "research"
  | "script"
  | "storyboard_review"
  | "voice"
  | "video_generation"
  | "assembly"
  | "captions"
  | "thumbnail"
  | "completed"
  | "failed";

export interface Project {
  id: string;
  owner_id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface Video {
  id: string;
  project_id: string;
  topic: string;
  target_duration_seconds: number;
  voice_preset: string;
  style_preset: string;
  stage: PipelineStage;
  stage_progress_percent: number;
  stage_detail: string;
  storyboard_approved: boolean;
  final_video_path: string | null;
  created_at: string;
  updated_at: string;
}

export type TransitionType = "cut" | "fade" | "dissolve";

export interface Scene {
  id: string;
  order: number;
  narration: string;
  visual_prompt: string;
  duration_seconds: number;
  transition: TransitionType;
}

export interface Script {
  id: string;
  video_id: string;
  title: string;
  hook: string;
  estimated_duration_seconds: number;
  word_count: number;
  approved: boolean;
  scenes: Scene[];
  created_at: string;
  updated_at: string;
}
