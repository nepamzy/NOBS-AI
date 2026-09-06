import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [pinCode, setPinCode] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await signup(pinCode, email, password, displayName);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-8">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-accent-500" />
          <span className="font-heading text-lg font-semibold tracking-tight text-white">
            NOBS AI
          </span>
        </div>

        <h1 className="font-heading text-2xl font-semibold text-white">Create your account</h1>
        <p className="mt-1 text-sm text-white/60">
          Enter the PIN the admin sent you — it expires 5 minutes after being generated and works
          once.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-white/70">Invite PIN</span>
            <input
              required
              autoFocus
              maxLength={6}
              inputMode="numeric"
              value={pinCode}
              onChange={(e) => setPinCode(e.target.value.replace(/\D/g, ""))}
              placeholder="123456"
              className="rounded-md border border-white/10 bg-white/5 px-3 py-2 tracking-[0.3em] text-white placeholder:tracking-normal placeholder:text-white/30"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-white/70">Name</span>
            <input
              required
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-white"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-white/70">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-white"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-white/70">Password</span>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-white"
            />
          </label>

          {error && (
            <p className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="mt-2 rounded-md bg-accent-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-600 disabled:opacity-40"
          >
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>
      </div>
    </div>
  );
}
