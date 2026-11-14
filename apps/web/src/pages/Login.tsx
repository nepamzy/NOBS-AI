import { useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { ApiError, warmApi } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Logo } from "../components/Logo";
import { useSlow } from "../hooks/useSlow";

export function Login() {
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const slowSignIn = useSlow(submitting, 4000);

  // Start waking the API now, while the email and password are being typed.
  useEffect(() => {
    warmApi();
  }, []);

  // Already signed in (e.g. tapped the logo again from the landing page):
  // no need to show the form.
  if (!loading && user && !submitting) {
    const from = (location.state as { from?: Location })?.from;
    return <Navigate to={from ? `${from.pathname}${from.search}` : "/dashboard"} replace />;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email, password);
      const from = (location.state as { from?: Location })?.from;
      navigate(from ? `${from.pathname}${from.search}` : "/dashboard", { replace: true });
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
          <Logo size={28} />
          <span className="font-heading text-lg font-semibold tracking-tight text-white">
            NOBS AI
          </span>
        </div>

        <h1 className="font-heading text-2xl font-semibold text-white">Log in</h1>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-white/70">Email</span>
            <input
              type="email"
              required
              autoFocus
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
            {submitting
              ? slowSignIn
                ? "Waking up the server… (up to a minute)"
                : "Logging in…"
              : "Log in"}
          </button>
        </form>

        <p className="mt-6 text-xs text-white/40">
          Only invited — signup needs a PIN from the admin.
        </p>
      </div>
    </div>
  );
}
