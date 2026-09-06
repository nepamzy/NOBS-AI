import type {
  Asset,
  CostCategory,
  Project,
  Scene,
  Script,
  Settings,
  SpendSummary,
  StylePreset,
  Video,
  VoicePreset,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// Video/Asset urls (e.g. "/storage/...") come back relative to the API
// server, not the frontend dev server — this makes them fetchable.
export function resolveStorageUrl(url: string | null): string | null {
  if (!url) return null;
  return `${BASE_URL}${url}`;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // response body wasn't JSON — fall back to statusText
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  listProjects: () => request<Project[]>("/projects"),
  createProject: (name: string) =>
    request<Project>("/projects", { method: "POST", body: JSON.stringify({ name }) }),
  getProject: (id: string) => request<Project>(`/projects/${id}`),

  listVideos: (projectId: string) =>
    request<Video[]>(`/videos?project_id=${encodeURIComponent(projectId)}`),
  listAllVideos: () => request<Video[]>("/videos"),
  createVideo: (payload: {
    project_id: string;
    topic: string;
    target_duration_seconds: number;
    voice_preset?: string;
    style_preset?: string;
    run_research: boolean;
  }) => request<Video>("/videos", { method: "POST", body: JSON.stringify(payload) }),
  getVideo: (id: string) => request<Video>(`/videos/${id}`),
  getVideoScript: (id: string) => request<Script>(`/videos/${id}/script`),
  approveStoryboard: (id: string) =>
    request<Video>(`/videos/${id}/approve-storyboard`, { method: "POST" }),
  updateScene: (videoId: string, sceneId: string, payload: Partial<Scene>) =>
    request<Scene>(`/videos/${videoId}/scenes/${sceneId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  regenerateScene: (videoId: string, sceneId: string) =>
    request<Scene>(`/videos/${videoId}/scenes/${sceneId}/regenerate`, { method: "POST" }),
  listAssets: (videoId: string) => request<Asset[]>(`/videos/${videoId}/assets`),

  getSettings: () => request<Settings>("/settings"),
  updateSettings: (payload: Partial<Settings>) =>
    request<Settings>("/settings", { method: "PUT", body: JSON.stringify(payload) }),

  getSpend: () => request<SpendSummary>("/spend"),
  createSpendEntry: (payload: {
    category: CostCategory;
    service: string;
    purpose: string;
    estimated_cost_usd?: number | null;
    actual_cost_usd?: number | null;
  }) => request<void>("/spend", { method: "POST", body: JSON.stringify(payload) }),

  listVoices: () => request<VoicePreset[]>("/voices"),
  listStyles: () => request<StylePreset[]>("/styles"),
};
