import { CheckCircle2, Lock } from "lucide-react";
import type { FormEvent } from "react";
import { useState } from "react";
import { ApiError, googleOAuthStartUrl, joinWaitlist } from "../api/client";

// Shared by the Home page's compact waitlist card and the full /waitlist
// page — same form, same two OAuth buttons, so there's one place to fix
// if the backend contract changes.
export function WaitlistInlineForm({ compact = false }: { compact?: boolean }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [joined, setJoined] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await joinWaitlist(email.trim(), name.trim());
      setJoined(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong — try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (joined) {
    return (
      <div className="mt-6 flex flex-col items-center gap-2.5 rounded-2xl border border-white/10 bg-black/20 py-7 text-center">
        <CheckCircle2 size={32} className="text-gold-400" />
        <p className="font-heading text-base font-semibold text-white">You're on the list</p>
        <p className="max-w-xs text-sm text-white/55">
          We'll email {email.trim() || "you"} the moment NOBS AI opens up. No account, nothing
          else to do.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-3">
      {!compact && (
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Your name (optional)"
          className="rounded-md border border-white/10 bg-black/20 px-3.5 py-2.5 text-sm text-white placeholder:text-white/30"
        />
      )}
      <input
        type="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Enter your email address"
        className="rounded-md border border-white/10 bg-black/20 px-3.5 py-2.5 text-sm text-white placeholder:text-white/30"
      />

      {error && <p className="text-sm text-red-400">{error}</p>}

      <button
        type="submit"
        disabled={submitting || !email.trim()}
        className="rounded-full bg-gradient-to-r from-gold-400 to-gold-500 px-6 py-3 text-sm font-semibold text-black transition-opacity disabled:opacity-40"
      >
        {submitting ? "Joining…" : "Join Waitlist →"}
      </button>

      <div className="my-1 flex items-center gap-3 text-xs text-white/30">
        <span className="h-px flex-1 bg-white/10" />
        or
        <span className="h-px flex-1 bg-white/10" />
      </div>

      <a
        href={googleOAuthStartUrl("google")}
        className="flex items-center justify-center gap-2.5 rounded-full border border-white/15 bg-black/20 px-5 py-2.5 text-sm font-medium text-white/85 transition-colors hover:border-white/30 hover:text-white"
      >
        <GoogleG />
        Continue with Google
      </a>
      <a
        href={googleOAuthStartUrl("youtube")}
        className="flex items-center justify-center gap-2.5 rounded-full border border-white/15 bg-black/20 px-5 py-2.5 text-sm font-medium text-white/85 transition-colors hover:border-white/30 hover:text-white"
      >
        <span className="text-red-500">▶</span>
        Continue with YouTube
      </a>

      <p className="mt-1 flex items-center justify-center gap-1.5 text-[11px] text-white/35">
        <Lock size={11} />
        Your information is safe with us.
      </p>
    </form>
  );
}

function GoogleG() {
  return (
    <svg width="16" height="16" viewBox="0 0 48 48" aria-hidden="true">
      <path
        fill="#FFC107"
        d="M43.6 20.5H42V20H24v8h11.3c-1.6 4.7-6.1 8-11.3 8-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34.5 6 29.5 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.7-.4-3.5z"
      />
      <path
        fill="#FF3D00"
        d="M6.3 14.7l6.6 4.8C14.6 16 18.9 13 24 13c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34.5 6 29.5 4 24 4c-7.4 0-13.8 4.2-17.7 10.7z"
      />
      <path
        fill="#4CAF50"
        d="M24 44c5.4 0 10.3-2 14-5.3l-6.5-5.3c-2 1.4-4.6 2.3-7.5 2.3-5.2 0-9.6-3.3-11.2-7.9l-6.5 5C9.9 39.6 16.4 44 24 44z"
      />
      <path
        fill="#1976D2"
        d="M43.6 20.5H42V20H24v8h11.3c-.8 2.3-2.2 4.2-4.1 5.5l6.5 5.3C41.3 36 44 30.6 44 24c0-1.3-.1-2.7-.4-3.5z"
      />
    </svg>
  );
}
