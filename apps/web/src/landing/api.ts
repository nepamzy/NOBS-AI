// Points at the same backend as the real app (apps/web) — the waitlist
// endpoint lives there (apps/api/app/routers/waitlist.py) so a signup
// lands in the same database Nobert already has open, no separate
// service to stand up just for this.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// Points the browser straight at the backend's redirect endpoint (see
// apps/api/app/routers/waitlist_oauth.py) rather than fetching it — this
// has to be a real navigation so Google's consent screen can load. If
// GOOGLE_WAITLIST_CLIENT_ID isn't configured yet, that endpoint redirects
// back here with ?oauth_error=not_configured instead of erroring, so the
// button always does *something* reasonable even before Nobert finishes
// the Google Cloud setup.
export function googleOAuthStartUrl(provider: "google" | "youtube"): string {
  return `${BASE_URL}/waitlist/oauth/${provider}/start`;
}

export async function joinWaitlist(email: string, name: string): Promise<void> {
  const response = await fetch(`${BASE_URL}/waitlist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, name }),
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // body wasn't JSON — fall back to statusText
    }
    throw new ApiError(response.status, detail);
  }
}
