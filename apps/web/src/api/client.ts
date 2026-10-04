import type {
  AdminUser,
  Asset,
  AuthResponse,
  BillingType,
  ChatAttachment,
  ChatMessage,
  ChatResponse,
  Clip,
  CostCategory,
  CostEntry,
  CostStatus,
  Project,
  Scene,
  Script,
  Settings,
  SignupPin,
  SourceVideo,
  SpendSummary,
  StylePreset,
  TokenPackage,
  UploadSchedule,
  Video,
  VideoFeedback,
  VoicePreset,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const TOKEN_STORAGE_KEY = "nobs_ai_token";

// Video/Asset urls (e.g. "/storage/...") come back relative to the API
// server, not the frontend dev server — this makes them fetchable.
export function resolveStorageUrl(url: string | null): string | null {
  if (!url) return null;
  return `${BASE_URL}${url}`;
}

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function storeToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    // localStorage unavailable (private mode etc.) — session just won't persist across reloads
  }
}

export function clearStoredToken(): void {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // see storeToken
  }
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  // fetch() rejects with a bare TypeError when the request never got a
  // readable response: server asleep/unreachable, or a server crash (500s
  // from the API carry no CORS header, so the browser hides them too).
  if (err instanceof TypeError) {
    return "Couldn't reach the server — it may be waking up (try again in a minute) or the request failed on the server.";
  }
  return String(err);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
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

// Separate from request(): a file upload must NOT set Content-Type itself —
// the browser sets it (with the multipart boundary) when the body is a
// FormData instance. Setting it manually breaks the upload silently.
async function upload<T>(path: string, formData: FormData): Promise<T> {
  const token = getStoredToken();
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
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

  uploadToYoutube: (
    videoId: string,
    payload: { title: string; description: string; tags?: string[] },
  ) =>
    request<Video>(`/videos/${videoId}/youtube/upload`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  publishToYoutube: (videoId: string) =>
    request<Video>(`/videos/${videoId}/youtube/publish`, { method: "POST" }),

  addVideoFeedback: (videoId: string, note: string) =>
    request<VideoFeedback>(`/videos/${videoId}/feedback`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  listProjectFeedback: (projectId: string) =>
    request<VideoFeedback[]>(`/projects/${projectId}/feedback`),

  listSchedules: () => request<UploadSchedule[]>("/upload-schedules"),
  createSchedule: (payload: {
    project_id: string;
    day_of_week: number;
    trigger_time: string;
    topic: string;
    target_duration_seconds: number;
    voice_preset?: string;
    style_preset?: string;
    run_research?: boolean;
    auto_publish?: boolean;
  }) =>
    request<UploadSchedule>("/upload-schedules", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateSchedule: (id: string, payload: { enabled?: boolean; auto_publish?: boolean }) =>
    request<UploadSchedule>(`/upload-schedules/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteSchedule: (id: string) => request<void>(`/upload-schedules/${id}`, { method: "DELETE" }),

  getSettings: () => request<Settings>("/settings"),
  updateSettings: (payload: Partial<Settings>) =>
    request<Settings>("/settings", { method: "PUT", body: JSON.stringify(payload) }),

  getSpend: () => request<SpendSummary>("/spend"),
  createSpendEntry: (payload: {
    category: CostCategory;
    service: string;
    purpose: string;
    status?: CostStatus;
    billing_type?: BillingType | null;
    estimated_cost_usd?: number | null;
    actual_cost_usd?: number | null;
  }) => request<CostEntry>("/spend", { method: "POST", body: JSON.stringify(payload) }),
  updateSpendEntry: (
    id: string,
    payload: {
      status?: CostStatus;
      billing_type?: BillingType | null;
      estimated_cost_usd?: number | null;
      actual_cost_usd?: number | null;
    },
  ) => request<CostEntry>(`/spend/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteSpendEntry: (id: string) => request<void>(`/spend/${id}`, { method: "DELETE" }),

  listVoices: () => request<VoicePreset[]>("/voices"),
  listStyles: () => request<StylePreset[]>("/styles"),

  signup: (payload: {
    pin_code: string;
    email: string;
    password: string;
    display_name: string;
  }) => request<AuthResponse>("/auth/signup", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload: { email: string; password: string }) =>
    request<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  me: () => request<AdminUser>("/auth/me"),
  changePassword: (payload: { current_password: string; new_password: string }) =>
    request<AdminUser>("/auth/password", { method: "PUT", body: JSON.stringify(payload) }),

  generatePin: () => request<SignupPin>("/admin/pins", { method: "POST" }),
  listUsers: () => request<AdminUser[]>("/admin/users"),
  suspendUser: (id: string) => request<AdminUser>(`/admin/users/${id}/suspend`, { method: "POST" }),
  unsuspendUser: (id: string) =>
    request<AdminUser>(`/admin/users/${id}/unsuspend`, { method: "POST" }),
  deleteUser: (id: string) => request<void>(`/admin/users/${id}`, { method: "DELETE" }),
  grantTokens: (id: string, amount: number) =>
    request<AdminUser>(`/admin/users/${id}/grant-tokens`, {
      method: "POST",
      body: JSON.stringify({ amount }),
    }),

  listPackages: () => request<TokenPackage[]>("/payments/packages"),

  sendChatMessage: (message: string, history: ChatMessage[], attachment?: ChatAttachment) =>
    request<ChatResponse>("/chat/messages", {
      method: "POST",
      body: JSON.stringify({ message, history, attachment: attachment ?? null }),
    }),

  uploadSourceVideo: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return upload<SourceVideo>("/source-videos", formData);
  },
  listSourceVideos: () => request<SourceVideo[]>("/source-videos"),
  getSourceVideo: (id: string) => request<SourceVideo>(`/source-videos/${id}`),
  updateSourceVideo: (id: string, payload: { auto_publish?: boolean }) =>
    request<SourceVideo>(`/source-videos/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  listClips: (sourceVideoId: string) =>
    request<Clip[]>(`/source-videos/${sourceVideoId}/clips`),
  publishClip: (clipId: string) => request<Clip>(`/clips/${clipId}/publish`, { method: "POST" }),
};
