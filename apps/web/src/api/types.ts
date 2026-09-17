// Mirrors apps/api/app/schemas/* and app/models/enums.py — keep in sync by hand
// until the API ships an OpenAPI-generated client.

export type PipelineStage =
  | "topic"
  | "research"
  | "script"
  | "storyboard_review"
  | "compliance_check"
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
  final_video_url: string | null;
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

export type AssetType =
  | "script"
  | "voiceover"
  | "scene_clip"
  | "thumbnail"
  | "captions"
  | "final_video";

export interface Asset {
  id: string;
  video_id: string;
  asset_type: AssetType;
  path: string;
  url: string | null;
  label: string;
  created_at: string;
}

export interface Settings {
  default_duration_minutes: number;
  default_voice_preset: string;
  default_style_preset: string;
  weekly_goal: number;
}

export type CostCategory =
  | "gpu"
  | "llm"
  | "tts"
  | "video_generation"
  | "storage"
  | "database"
  | "hosting"
  | "networking"
  | "domain"
  | "other";

export interface CostEntry {
  id: string;
  category: CostCategory;
  service: string;
  purpose: string;
  video_id: string | null;
  estimated_cost_usd: number | null;
  actual_cost_usd: number | null;
  occurred_at: string;
}

export interface SpendSummary {
  entries: CostEntry[];
  total_estimated_usd: number;
  total_actual_usd: number;
}

export interface VoicePreset {
  id: string;
  name: string;
  description: string;
  preview_path: string | null;
}

export interface StylePreset {
  id: string;
  name: string;
  description: string;
  accent_hex: string;
}

export type UserRole = "admin" | "user";

export interface AdminUser {
  id: string;
  email: string;
  display_name: string;
  role: UserRole;
  is_suspended: boolean;
  token_balance: number;
  created_at: string;
}

export interface AuthResponse {
  token: string;
  user: AdminUser;
}

export interface SignupPin {
  code: string;
  expires_at: string;
}

export interface TokenPackage {
  id: string;
  name: string;
  tokens: number;
  price_usd: number;
}

// `content` mirrors the Anthropic Messages API shape: a plain string for a
// simple turn, or a list of content blocks (text/tool_use/tool_result) once
// tool calls are involved — the UI only ever renders the text parts.
export interface ChatMessage {
  role: "user" | "assistant";
  content: string | Record<string, unknown>[];
}

export interface ChatAttachment {
  media_type: string;
  data: string; // base64, no data: URL prefix
  filename?: string;
}

export interface GeneratedFile {
  filename: string;
  media_type: string;
  url: string | null;
}

export interface ChatResponse {
  reply: string;
  files: GeneratedFile[];
  history: ChatMessage[];
}
